from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import List
import httpx
import jwt
from pwdlib import PasswordHash
from app.core.security import decode_token
from app.core.utils import hash_str
from app.models.user import User
from app.core.exceptions import KeycloakExchangeFailed, TokenInvalid, UserNotFound
from app.core.config import get_settings
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.mail_service import MailService

password_hash = PasswordHash.recommended()
ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)
FORGET_PASSWORD_TOKEN_EXPIRE = timedelta(minutes=10)


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        mail_service: MailService,
    ):
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.mail_service = mail_service

    async def authenticate_user(self, email: str, password: str):
        user = await self.user_repository.get_by_email(email)
        if not user:
            return False
        if not self.verify_password(password, user.password):
            return False
        return user

    async def create_access_token(self, user: User):
        roles = await self.user_repository.get_roles_list(user)
        to_encode = {"sub": user.email, "roles": roles}
        expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, get_settings().SECRET_KEY, algorithm="HS256"
        )
        return encoded_jwt

    async def create_refresh_token(self, user: User):
        raw_token = secrets.token_urlsafe(64)
        hashed_token = hash_str(raw_token)
        token = await self.user_repository.create_refresh_token_by_user(
            user,
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
        hashed_token = hash_str(raw_token)
        token = await self.user_repository.get_refresh_token(hashed_token)
        if not token:
            return None
        else:
            return token

    def verify_password(self, plain_password: str, hashed_password: str):
        return password_hash.verify(plain_password, hashed_password)

    def hash_password(self, password: str):
        return password_hash.hash(password)

    async def create_forget_password_token(self, email: str, user: User):
        token = secrets.token_urlsafe(32)

        expire = datetime.now(timezone.utc) + FORGET_PASSWORD_TOKEN_EXPIRE

        await self.user_repository.save_forget_password_token(token, user, expire)

        return token

    async def register_user(self, user: User):

        user.password = self.hash_password(user.password)

        user.is_admin = False
        user.is_staff = False
        user.is_company = True

        try:
            return await self.user_repository.create_user(user)
        except Exception as e:
            raise e

    async def login_user(self, username: str, password: str):
        user = await self.authenticate_user(username, password)
        if not user:
            raise UserNotFound("User Not Found During Login")
        return await self.create_tokens(user)

    async def refresh_user(self, refresh_token: str):
        if not refresh_token:
            raise TokenInvalid("Refresh Token Invalid")

        token = await self.verify_refresh_token(refresh_token)

        if (
            not token
            or token.is_revoked
            or datetime.now(timezone.utc) > token.expires_at.astimezone(timezone.utc)
        ):
            raise TokenInvalid("Refresh Token Invalid")

        user = await self.user_repository.get_by_id(token.user_id)

        if not user:
            raise TokenInvalid("Refresh Token Invalid")

        return await self.create_tokens(user)

    async def forget_password(self, email: str):
        user = await self.user_repository.get_by_email(email)

        if not user:
            return None

        token = await self.create_forget_password_token(email, user)

        await self.mail_service.send_forget_password_mail(email, token)

    async def reset_password(self, token: str, new_password: str):
        if not await self.validate_reset_token(token):
            raise TokenInvalid("Reset Password Token Expired")
        try:
            return await self.user_repository.change_password(
                token, self.hash_password(new_password)
            )
        except Exception as e:
            raise e

    async def validate_reset_token(self, token: str):
        return await self.user_repository.check_forget_password_token(token)

    async def keycloak_callback(self, code: str):
        settings = get_settings()
        token_url = settings.KEYCLOAK_TOKEN_URL

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
            "redirect_uri": settings.KEYCLOAK_CALLBACK,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=payload)

        if response.status_code != 200:
            raise KeycloakExchangeFailed("Keycloak return non-200 status code")

        decoded_token = decode_token(response.json().get("access_token"))

        return await self.login_keycloak_user(decoded_token)

    async def login_keycloak_user(self, decoded_token: str):
        user = await self.map_keycloak_to_user(decoded_token)
        
        return await self.create_refresh_token(user)
        
    async def map_keycloak_to_user(self, decoded_token: str):
        email = decoded_token["email"]
        keycloak_roles = decoded_token["resource_access"][
            get_settings().KEYCLOAK_CLIENT_ID
        ]["roles"]
        sub = decoded_token["sub"]
        first_name = decoded_token["given_name"]
        last_name = decoded_token["family_name"]

        admin, roles = await self.map_keycloak_roles(
            keycloak_roles, ["vis-active", "admin"]
        )

        return await self.user_repository.create_or_update_user(
            User(
                email=email,
                sub=sub,
                roles=roles,
                is_confirmed=True,
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
