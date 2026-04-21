from datetime import datetime, timedelta, timezone
import asyncio
import secrets
import logging
from typing import List
import httpx
import jwt
import phonenumbers
from pwdlib import PasswordHash
from app.core.security import decode_token
from app.core.utils import hash_str
from app.models.user import User
from app.core.exceptions import (
    EmailUsed,
    KeycloakExchangeFailed,
    PasswordTooShort,
    PasswordWrong,
    PhoneNumberInvalid,
    TokenInvalid,
    NotAllowed,
)
from app.core.config import get_settings
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.token_repository import TokenRepository
from app.services.mail_service import MailService

logger = logging.getLogger(__name__)

password_hash = PasswordHash.recommended()
ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)
FORGET_PASSWORD_TOKEN_EXPIRE = timedelta(minutes=10)


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: TokenRepository,
        role_repository: RoleRepository,
        mail_service: MailService,
    ):
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.role_repository = role_repository
        self.mail_service = mail_service

    async def authenticate_user(self, email: str, password: str):
        user = await self.user_repository.get_by_email(email)
        if not user:
            return False
        if not await self.verify_password(password, user.password):
            return False
        return user

    async def create_access_token(self, user: User):
        to_encode = {"sub": user.email}
        expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, get_settings().SECRET_KEY, algorithm="HS256")

    async def create_refresh_token(self, user: User):
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

    async def create_tokens(self, user: User):
        access_token = await self.create_access_token(user)
        refresh_token = await self.create_refresh_token(user)
        return (access_token, refresh_token)

    async def verify_refresh_token(self, raw_token: str):
        return await self.token_repository.get_refresh_token(hash_str(raw_token))

    async def verify_password(self, plain_password: str, hashed_password: str):
        return await asyncio.to_thread(password_hash.verify, plain_password, hashed_password)

    async def hash_password(self, password: str):
        return await asyncio.to_thread(password_hash.hash, password)

    async def create_forget_password_token(self, user: User):
        raw_token = secrets.token_urlsafe(32)
        hashed_token = hash_str(raw_token)
        expire = datetime.now(timezone.utc) + FORGET_PASSWORD_TOKEN_EXPIRE
        await self.token_repository.save_forget_password_token(hashed_token, user.id, expire)
        return raw_token

    async def register_user(self, user: User):
        if await self.user_repository.get_by_email(user.email):
            raise EmailUsed(f"register_user:{user.email}")

        if len(user.password) < 10:
            raise PasswordTooShort("register:register_password_too_short")

        if user.phone_number:
            phone_number = phonenumbers.parse(user.phone_number, "CH")
            if not phonenumbers.is_valid_number(phone_number):
                raise PhoneNumberInvalid("register:phone_number_invalid")
            user.phone_number = phonenumbers.format_number(
                phone_number, phonenumbers.PhoneNumberFormat.E164
            )

        user.password = await self.hash_password(user.password)
        user.is_admin = False
        user.is_staff = False
        user.is_company = True

        try:
            result = await self.user_repository.create_user(user)
            logger.info(f"User registered: {user.email}")
            return result
        except Exception as e:
            logger.error(f"User registration failed: {user.email} - {str(e)}")
            raise e

    async def login_user(self, username: str, password: str):
        user = await self.authenticate_user(username, password)
        if not user:
            logger.warning(f"Login failed: invalid credentials for {username}")
            raise PasswordWrong(f"login:{username}")
        logger.info(f"User login successful: {username}")
        return await self.create_tokens(user)

    async def refresh_user(self, refresh_token: str):
        if not refresh_token:
            raise TokenInvalid("refresh:no_token")

        token = await self.verify_refresh_token(refresh_token)

        if (
            not token
            or token.is_revoked
            or datetime.now(timezone.utc) > token.expires_at.astimezone(timezone.utc)
        ):
            raise TokenInvalid(f"refresh:{token.user_id if token else 'unknown'}")

        user = await self.user_repository.get_by_id(token.user_id)

        if not user:
            raise TokenInvalid(f"refresh:{token.user_id}")

        await self.token_repository.revoke_refresh_token(user.id, hash_str(refresh_token))

        return await self.create_tokens(user)

    async def forget_password(self, email: str):
        user = await self.user_repository.get_by_email(email)

        if not user:
            logger.debug(f"Forget password request for non-existent user: {email}")
            return None

        if not user.password:
            logger.warning(f"Forget password requested for OAuth-only user: {email}")
            raise NotAllowed(f"forget_password:{user.id}")

        token = await self.create_forget_password_token(user)
        logger.info(f"Password reset token created for user: {email}")
        await self.mail_service.send_forget_password_mail(email, token)

    async def reset_password(self, token: str, new_password: str):
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

    async def validate_reset_token(self, token: str):
        return await self.token_repository.get_forget_password_token(hash_str(token)) is not None

    async def keycloak_callback(self, code: str):
        settings = get_settings()
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.SIP_AUTH_OIDC_CLIENT_ID,
            "client_secret": settings.SIP_AUTH_OIDC_CLIENT_SECRET,
            "redirect_uri": settings.KEYCLOAK_CALLBACK,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(settings.SIP_AUTH_OIDC_TOKEN_ENDPOINT, data=payload)

        if response.status_code != 200:
            raise KeycloakExchangeFailed(f"keycloak_callback:{code}")

        decoded_token = decode_token(response.json().get("access_token"))
        if not decoded_token:
            raise KeycloakExchangeFailed(f"keycloak_callback:invalid_token:{code}")
        return await self.login_keycloak_user(decoded_token)

    async def login_keycloak_user(self, decoded_token: str):
        user = await self.map_keycloak_to_user(decoded_token)
        return await self.create_refresh_token(user)

    async def map_keycloak_to_user(self, decoded_token: str):
        email = decoded_token["email"]
        if get_settings().DEBUG_KEYCLOAK_ADMIN:
            keycloak_roles = [get_settings().ADMIN_GROUP]
        else:
            keycloak_roles = (
                decoded_token
                .get("resource_access", {})
                .get(get_settings().SIP_AUTH_OIDC_CLIENT_ID, {})
                .get("roles", [])
            )
        sub = decoded_token["sub"]
        first_name = decoded_token.get("given_name", "")
        last_name = decoded_token.get("family_name", "")

        admin, roles = await self.map_keycloak_roles(keycloak_roles, ["vis-active", "admin"])

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

    async def map_keycloak_roles(self, roles: List[str], vis_groups: List[str]):
        result = []
        admin = False
        for role in roles:
            if role in vis_groups:
                result.append(await self.role_repository.get_or_create(role))
                if role == get_settings().ADMIN_GROUP:
                    admin = True
        return (admin, result)
