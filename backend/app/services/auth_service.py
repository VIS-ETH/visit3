import asyncio
import logging
import secrets
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx
import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.exceptions import (
    EmailUsed,
    InvalidCredentials,
    KeycloakExchangeFailed,
    NotAllowed,
    PasswordTooShort,
    PhoneNumberInvalid,
    TokenInvalid,
)
from app.core.security import decode_token
from app.core.utils import hash_str, normalize_phone_number
from app.models.user import RefreshToken, Role, User
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.mail_service import MailService

logger = logging.getLogger(__name__)

password_hash = PasswordHash.recommended()
ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)
FORGET_PASSWORD_TOKEN_EXPIRE = timedelta(minutes=10)
CONFIRM_EMAIL_TOKEN_EXPIRE = timedelta(days=3)
MIN_PASSWORD_LENGTH = 10


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: TokenRepository,
        role_repository: RoleRepository,
        mail_service: MailService,
    ) -> None:
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.role_repository = role_repository
        self.mail_service = mail_service

    async def authenticate_user(
        self, email: str, password: str
    ) -> User | Literal[False]:
        user = await self.user_repository.get_by_email(email)
        if not user:
            return False
        valid_password = await self.verify_and_update_password(user, password)
        if not valid_password:
            return False
        return user

    async def create_access_token(self, user: User) -> str:
        to_encode: dict[str, Any] = {
            "sub": str(
                user.id
            ),  # we use the internal user id as the subject to have a uniform way to identify users, regardless of the login method (keycloak or password)
            "email": user.email,
        }
        expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, get_settings().SECRET_KEY, algorithm="HS256")

    async def create_refresh_token(self, user: User) -> str:
        raw_token = secrets.token_urlsafe(64)
        hashed_token = hash_str(raw_token)
        token = await self.token_repository.create_refresh_token(
            user.id,
            hashed_token,
            datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRE,
        )

        if not token:
            raise Exception

        return raw_token

    async def create_tokens(self, user: User) -> tuple[str, str]:
        access_token = await self.create_access_token(user)
        refresh_token = await self.create_refresh_token(user)
        return (access_token, refresh_token)

    async def get_active_refresh_token(self, raw_token: str) -> RefreshToken | None:
        return await self.token_repository.get_active_refresh_token(hash_str(raw_token))

    async def verify_and_update_password(self, user: User, plain_password: str) -> bool:
        if user.password is None:
            return False
        valid, updated_hash = await asyncio.to_thread(
            password_hash.verify_and_update,
            plain_password,
            user.password,
        )
        if not valid:
            return False
        if updated_hash is not None:
            try:
                await self.user_repository.update_password(user.id, updated_hash)
            except Exception:
                logger.exception(f"Failed to rehash password for user: {user.email}")
        return True

    async def hash_password(self, password: str) -> str:
        return await asyncio.to_thread(password_hash.hash, password)

    async def create_forget_password_token(self, user: User) -> str:
        raw_token = secrets.token_urlsafe(32)
        hashed_token = hash_str(raw_token)
        expire = datetime.now(timezone.utc) + FORGET_PASSWORD_TOKEN_EXPIRE
        await self.token_repository.save_forget_password_token(
            hashed_token, user.id, expire
        )
        return raw_token

    async def create_confirm_email_token(self, user: User) -> str:
        raw_token = secrets.token_urlsafe(32)
        hashed_token = hash_str(raw_token)
        expire = datetime.now(timezone.utc) + CONFIRM_EMAIL_TOKEN_EXPIRE
        await self.token_repository.save_confirm_email_token(
            hashed_token, user.id, expire
        )
        return raw_token

    async def send_confirm_email(self, user: User) -> None:
        if user.email_confirmed:
            return
        await self.token_repository.revoke_confirm_email_tokens(user.id)
        raw_token = await self.create_confirm_email_token(user)
        await self.mail_service.send_confirm_email_mail(user.email, raw_token)

    async def register_user(self, user: User) -> User:
        if await self.user_repository.get_by_email(user.email):
            raise EmailUsed(f"register_user:{user.email}")

        if not user.password:
            raise PasswordTooShort("register:password_required")

        if len(user.password) < MIN_PASSWORD_LENGTH:
            raise PasswordTooShort("register:register_password_too_short")

        if user.phone_number:
            try:
                user.phone_number = normalize_phone_number(user.phone_number)
            except Exception:
                raise PhoneNumberInvalid("register:phone_number_invalid")

        user.password = await self.hash_password(user.password)
        user.is_admin = False
        user.is_staff = False
        user.is_company = True

        try:
            result = await self.user_repository.create_user(user)
            await self.send_confirm_email(result)
            logger.info(f"User registered: {user.email}")
            return result
        except Exception as e:
            logger.error(f"User registration failed: {user.email} - {str(e)}")
            raise e

    async def login_user(self, username: str, password: str) -> tuple[str, str]:
        user = await self.authenticate_user(username, password)
        if not user:
            logger.warning(f"Login failed: invalid credentials for {username}")
            raise InvalidCredentials(f"login:{username}")
        logger.info(f"User login successful: {username}")
        return await self.create_tokens(user)

    async def refresh_user(self, refresh_token: str) -> tuple[str, str]:
        if not refresh_token:
            raise TokenInvalid("refresh:no_token")

        token = await self.get_active_refresh_token(refresh_token)

        if not token:
            raise TokenInvalid(f"refresh:{token.user_id if token else 'unknown'}")

        user = await self.user_repository.get_by_id(token.user_id)

        if not user:
            raise TokenInvalid(f"refresh:{token.user_id}")

        await self.token_repository.revoke_refresh_token(
            user.id, hash_str(refresh_token)
        )

        return await self.create_tokens(user)

    async def forget_password(self, email: str) -> None:
        user = await self.user_repository.get_by_email(email)

        if not user:
            logger.debug(f"Forget password request for non-existent user: {email}")
            return

        if not user.password:
            logger.warning(f"Forget password requested for OAuth-only user: {email}")
            raise NotAllowed(f"forget_password:{user.id}")

        token = await self.create_forget_password_token(user)
        logger.info(f"Password reset token created for user: {email}")
        await self.mail_service.send_forget_password_mail(email, token)

    async def reset_password(self, token: str, new_password: str) -> bool:
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise PasswordTooShort("reset_password:password_too_short")

        hashed = hash_str(token)
        forget_token = await self.token_repository.get_forget_password_token(hashed)

        if not forget_token:
            logger.warning("Password reset attempted with invalid/expired token")
            raise TokenInvalid("reset_password")

        try:
            await self.user_repository.update_password(
                forget_token.user_id, await self.hash_password(new_password)
            )
            await self.token_repository.revoke_all_refresh_tokens(forget_token.user_id)
            await self.token_repository.revoke_forget_password_token(hashed)
            logger.info("Password reset successful")
            return True
        except Exception as e:
            logger.error(f"Password reset failed: {str(e)}")
            raise e

    async def validate_reset_token(self, token: str) -> bool:
        return (
            await self.token_repository.get_forget_password_token(hash_str(token))
            is not None
        )

    async def validate_confirm_email_token(self, token: str) -> bool:
        return (
            await self.token_repository.get_confirm_email_token(hash_str(token))
            is not None
        )

    async def confirm_email(self, token: str) -> bool:
        hashed = hash_str(token)
        confirm_token = await self.token_repository.get_confirm_email_token(hashed)
        if not confirm_token:
            logger.warning("Email confirmation attempted with invalid/expired token")
            raise TokenInvalid("confirm_email")

        user = await self.user_repository.get_by_id(confirm_token.user_id)
        if not user:
            logger.warning(
                f"Email confirmation attempted for missing user: {confirm_token.user_id}"
            )
            raise TokenInvalid("confirm_email:user_not_found")

        await self.user_repository.confirm_email(user)
        await self.token_repository.revoke_confirm_email_tokens(user.id)
        logger.info(f"Email confirmed for user: {user.email}")
        return True

    async def keycloak_callback(self, code: str) -> str:
        settings = get_settings()
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.SIP_AUTH_OIDC_CLIENT_ID,
            "client_secret": settings.SIP_AUTH_OIDC_CLIENT_SECRET,
            "redirect_uri": settings.KEYCLOAK_CALLBACK,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.SIP_AUTH_OIDC_TOKEN_ENDPOINT, data=payload
            )

        if response.status_code != 200:
            raise KeycloakExchangeFailed(f"keycloak_callback:{code}")

        decoded_token = decode_token(response.json().get("access_token"))
        if not decoded_token:
            raise KeycloakExchangeFailed(f"keycloak_callback:invalid_token:{code}")
        return await self.login_keycloak_user(decoded_token)

    async def login_keycloak_user(self, decoded_token: dict[str, Any]) -> str:
        user = await self.map_keycloak_to_user(decoded_token)
        return await self.create_refresh_token(user)

    async def map_keycloak_to_user(self, decoded_token: dict[str, Any]) -> User:
        if get_settings().DEBUG_KEYCLOAK_ADMIN:
            keycloak_roles = [get_settings().ADMIN_GROUP]
        else:
            keycloak_roles = (
                decoded_token.get("resource_access", {})
                .get(get_settings().SIP_AUTH_OIDC_CLIENT_ID, {})
                .get("roles", [])
            )

        admin, roles = await self.map_keycloak_roles(
            keycloak_roles, ["vis-active", "admin"]
        )

        email = decoded_token["email"]
        sub = decoded_token["sub"]
        first_name = decoded_token.get("given_name", "")
        last_name = decoded_token.get("family_name", "")

        return await self.user_repository.create_or_update_user(
            User(
                email=email,
                sub=sub,
                roles=roles,
                user_confirmed=True,
                email_confirmed=True,
                is_admin=admin,
                is_staff=True,
                is_company=False,
                first_name=first_name,
                last_name=last_name,
            )
        )

    async def map_keycloak_roles(
        self, roles: Sequence[str], vis_groups: Sequence[str]
    ) -> tuple[bool, list[Role]]:
        result: list[Role] = []
        admin = False
        for role in roles:
            if role in vis_groups:
                result.append(await self.role_repository.get_or_create(role))
                if role == get_settings().ADMIN_GROUP:
                    admin = True
        return (admin, result)
