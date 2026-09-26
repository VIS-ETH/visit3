import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx
import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    EmailTakenLocally,
    EmailUsed,
    IdentityProviderUnavailable,
    InvalidCredentials,
    KeycloakExchangeFailed,
    MailUnavailable,
    NotVisMember,
    PasswordTooShort,
    PhoneNumberInvalid,
    TokenInvalid,
)
from app.core.security import decode_token
from app.core.utils import normalize_phone_number, strip_text
from app.mail_templates.context import (
    AccountAwaitingConfirmationContext,
    AccountConfirmEmailContext,
    AccountExistsContext,
    PasswordResetContext,
)
from app.mail_templates.keys import MailTemplateKey
from app.models.user import RefreshToken, Role, User
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.invite_service import InviteService
from app.services.mail_template_service import MailTemplateService

logger = logging.getLogger(__name__)

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("visit-dummy-password")
ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
MIN_PASSWORD_LENGTH = 8
UNKNOWN_NAME = "Unknown"
LOGIN_LINK_PATH = "/auth/link"
STAFF_ACCOUNT_REVIEW_PATH = "/user-management"


@dataclass(frozen=True)
class LoginLink:
    refresh_token: str
    target_path: str


def safe_target_path(target_path: str) -> str:
    if target_path.startswith("/") and not target_path.startswith("//"):
        return target_path
    return "/"


def frontend_url(path: str) -> str:
    return f"{get_settings().VISIT_FRONTEND_SERVER_URL}{path}"


def is_local_account(user: User) -> bool:
    return user.password is not None or user.is_company


def is_unclaimed_local_account(user: User) -> bool:
    return (
        user.sub is None
        and not user.email_confirmed
        and user.company_id is None
        and not user.is_staff
        and not user.is_admin
    )


def _claim(decoded_token: dict[str, Any], name: str) -> str:
    value = decoded_token.get(name)
    return strip_text(value) if isinstance(value, str) else ""


def _fallback_names(decoded_token: dict[str, Any]) -> tuple[str, str]:
    display = (
        _claim(decoded_token, "name")
        or _claim(decoded_token, "preferred_username")
        or _claim(decoded_token, "email").split("@")[0]
    )
    parts = display.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    if len(parts) == 1:
        return parts[0], UNKNOWN_NAME
    return UNKNOWN_NAME, UNKNOWN_NAME


def keycloak_names(decoded_token: dict[str, Any]) -> tuple[str, str]:
    given = _claim(decoded_token, "given_name")
    family = _claim(decoded_token, "family_name")
    if given and family:
        return given, family
    fallback_given, fallback_family = _fallback_names(decoded_token)
    return given or fallback_given, family or fallback_family


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: TokenRepository,
        role_repository: RoleRepository,
        mail_template_service: MailTemplateService,
        invite_service: InviteService,
    ) -> None:
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.role_repository = role_repository
        self.mail_template_service = mail_template_service
        self.invite_service = invite_service

    async def authenticate_user(
        self, email: str, password: str
    ) -> User | Literal[False]:
        user = await self.user_repository.get_by_email(email)
        if user is None or user.password is None:
            await asyncio.to_thread(
                password_hash.verify_and_update, password, DUMMY_PASSWORD_HASH
            )
            return False
        valid_password = await self.verify_and_update_password(user, password)
        if not valid_password:
            return False
        return user

    async def create_access_token(self, user: User) -> str:
        to_encode: dict[str, Any] = {
            "sub": str(user.id),
            "email": user.email,
        }
        expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, get_settings().SECRET_KEY, algorithm="HS256")

    async def create_refresh_token(self, user: User) -> str:
        return await self.token_repository.create_refresh_token(user.id)

    async def create_tokens(self, user: User) -> tuple[str, str]:
        access_token = await self.create_access_token(user)
        refresh_token = await self.create_refresh_token(user)
        return (access_token, refresh_token)

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
                logger.exception("Failed to rehash password for user: %s", user.id)
        return True

    async def hash_password(self, password: str) -> str:
        return await asyncio.to_thread(password_hash.hash, password)

    async def create_reset_password_token(self, user: User) -> str:
        return await self.token_repository.create_reset_password_token(user.id)

    async def create_confirm_email_token(self, user: User) -> str:
        return await self.token_repository.create_confirm_email_token(user.id)

    async def create_login_link(self, user: User, target_path: str) -> str:
        token = await self.token_repository.create_login_link_token(
            user.id, safe_target_path(target_path)
        )
        return frontend_url(f"{LOGIN_LINK_PATH}/{token}")

    async def consume_login_link(self, token: str) -> LoginLink:
        link_use = await self.token_repository.use_login_link_token(token)
        if not link_use:
            logger.warning("Login link used with an invalid, spent or expired token")
            raise TokenInvalid("login_link")

        user = await self.user_repository.get_by_id(link_use.user_id)
        if not user:
            raise TokenInvalid(f"login_link:{link_use.user_id}")

        refresh_token = await self.create_refresh_token(user)
        logger.info("Login link consumed for user: %s", user.id)
        return LoginLink(
            refresh_token=refresh_token,
            target_path=safe_target_path(link_use.target_path),
        )

    async def send_confirm_email(self, user: User) -> None:
        if user.email_confirmed:
            return
        await self.token_repository.revoke_confirm_email_tokens(user.id)
        token = await self.create_confirm_email_token(user)
        await self.mail_template_service.send(
            MailTemplateKey.ACCOUNT_CONFIRM_EMAIL,
            [user.email],
            AccountConfirmEmailContext(
                name=user.display_name,
                confirm_url=frontend_url(f"/confirm-email/{token}"),
            ),
        )

    async def register_user(self, user: User, invite_token: str | None = None) -> None:
        if not user.password:
            raise PasswordTooShort("register:password_required")

        if len(user.password) < MIN_PASSWORD_LENGTH:
            raise PasswordTooShort("register:register_password_too_short")

        if user.phone_number:
            try:
                user.phone_number = normalize_phone_number(user.phone_number)
            except Exception:
                raise PhoneNumberInvalid("register:phone_number_invalid")

        if invite_token is not None:
            invite = await self.invite_service.load_open_invite(
                invite_token, "register"
            )
            self.invite_service.ensure_email_matches(invite, user.email, "register")
            user.pending_invite_token = invite_token

        if await self.user_repository.get_by_email(user.email):
            await self.hash_password(user.password)
            await self._send_account_exists(user.email)
            return

        user.password = await self.hash_password(user.password)
        user.is_admin = False
        user.is_staff = False
        user.is_company = True

        try:
            result = await self.user_repository.create_user(user)
        except EmailUsed:
            await self._send_account_exists(user.email)
            return
        except Exception as e:
            logger.error("User registration failed: %s", e.__class__.__name__)
            raise e

        try:
            await self.send_confirm_email(result)
        except Exception as e:
            # Undo the registration so the email address can be used again.
            logger.error(
                "User registration failed for %s: %s", result.id, e.__class__.__name__
            )
            await self.user_repository.delete_user(result)
            raise e

        logger.info("User registered: %s", result.id)

    async def _send_account_exists(self, email: str) -> None:
        await self.mail_template_service.send(
            MailTemplateKey.ACCOUNT_EXISTS,
            [email],
            AccountExistsContext(
                login_url=frontend_url("/login"),
                reset_url=frontend_url("/reset-password"),
            ),
        )
        logger.info("Registration attempted for an existing account")

    async def login_user(self, username: str, password: str) -> tuple[str, str]:
        user = await self.authenticate_user(username, password)
        if not user:
            logger.warning("Login failed: invalid credentials")
            raise InvalidCredentials(f"login:{username}")
        logger.info("User login successful: %s", user.id)
        return await self.create_tokens(user)

    async def refresh_user(self, refresh_token: str) -> tuple[str, str]:
        if not refresh_token:
            raise TokenInvalid("refresh:no_token")

        token = await self.token_repository.get_refresh_token_for_rotation(
            refresh_token
        )

        if not token:
            await self._revoke_reused_family(refresh_token)
            raise TokenInvalid("refresh:unknown")

        user = await self.user_repository.get_by_id(token.user_id)

        if not user:
            raise TokenInvalid(f"refresh:{token.user_id}")

        idp_refresh_token = token.idp_refresh_token
        if user.sub is not None and not token.is_revoked:
            user, idp_refresh_token = await self._revalidate_sso_session(user, token)

        if not token.is_revoked:
            await self.token_repository.rotate_refresh_token(user.id, refresh_token)

        access_token = await self.create_access_token(user)
        next_refresh_token = await self.token_repository.create_refresh_token(
            user.id, family_id=token.family_id, idp_refresh_token=idp_refresh_token
        )
        return access_token, next_refresh_token

    async def _revoke_reused_family(self, refresh_token: str) -> None:
        stale = await self.token_repository.find_refresh_token(refresh_token)
        if stale is None or stale.rotated_at is None:
            return
        await self.token_repository.revoke_refresh_family(stale.family_id)
        logger.warning("Refresh token reuse detected for user %s", stale.user_id)

    async def _revalidate_sso_session(
        self, user: User, token: RefreshToken
    ) -> tuple[User, str]:
        if token.idp_refresh_token is None:
            await self.token_repository.revoke_refresh_family(token.family_id)
            raise TokenInvalid(f"refresh:sso_session_missing:{user.id}")
        settings = get_settings()
        try:
            response = await self._token_endpoint(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": token.idp_refresh_token,
                    "client_id": settings.SIP_AUTH_OIDC_CLIENT_ID,
                    "client_secret": (
                        settings.SIP_AUTH_OIDC_CLIENT_SECRET.get_secret_value()
                    ),
                }
            )
        except KeycloakExchangeFailed as error:
            raise IdentityProviderUnavailable(error.identifier) from None
        decoded_token = (
            decode_token(response.json().get("access_token"))
            if response.status_code == 200
            else None
        )
        if decoded_token is None:
            await self.token_repository.revoke_refresh_family(token.family_id)
            raise TokenInvalid(f"refresh:sso_session_ended:{user.id}")
        try:
            refreshed_user = await self.map_keycloak_to_user(decoded_token)
        except (NotVisMember, EmailTakenLocally, EmailUsed, KeycloakExchangeFailed):
            await self.token_repository.revoke_refresh_family(token.family_id)
            raise TokenInvalid(f"refresh:sso_rejected:{user.id}") from None
        if refreshed_user.id != user.id:
            await self.token_repository.revoke_refresh_family(token.family_id)
            raise TokenInvalid(f"refresh:sso_subject_changed:{user.id}")
        next_idp_token = response.json().get("refresh_token")
        return refreshed_user, next_idp_token or token.idp_refresh_token

    async def _token_endpoint(self, payload: dict[str, str]) -> httpx.Response:
        try:
            async with httpx.AsyncClient() as client:
                return await client.post(
                    get_settings().SIP_AUTH_OIDC_TOKEN_ENDPOINT, data=payload
                )
        except httpx.HTTPError as error:
            raise KeycloakExchangeFailed(
                f"keycloak:unreachable:{error.__class__.__name__}"
            ) from None

    async def request_password_reset(self, email: str) -> None:
        user = await self.user_repository.get_by_email(email)

        if not user:
            logger.debug("Password reset requested for a non-existent user")
            return

        if not user.password:
            logger.warning("Password reset requested for OAuth-only user: %s", user.id)
            return

        await self.token_repository.revoke_reset_password_tokens(user.id)
        token = await self.create_reset_password_token(user)
        logger.info("Password reset token created for user: %s", user.id)
        await self.mail_template_service.send(
            MailTemplateKey.PASSWORD_RESET,
            [user.email],
            PasswordResetContext(
                name=user.display_name, reset_url=frontend_url(f"/reset/{token}")
            ),
        )

    async def reset_password(self, token: str, new_password: str) -> bool:
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise PasswordTooShort("reset_password:password_too_short")

        reset_token = await self.token_repository.get_reset_password_token(token)

        if not reset_token:
            logger.warning("Password reset attempted with invalid/expired token")
            raise TokenInvalid("reset_password")

        try:
            await self.user_repository.update_password(
                reset_token.user_id, await self.hash_password(new_password)
            )
            await self.token_repository.revoke_all_refresh_tokens(reset_token.user_id)
            await self.token_repository.revoke_reset_password_tokens(
                reset_token.user_id
            )
            await self.token_repository.revoke_login_link_tokens(reset_token.user_id)
            logger.info("Password reset successful")
            return True
        except Exception as e:
            logger.error("Password reset failed: %r", e)
            raise e

    async def validate_reset_token(self, token: str) -> bool:
        return await self.token_repository.get_reset_password_token(token) is not None

    async def validate_confirm_email_token(self, token: str) -> bool:
        if await self.token_repository.get_confirm_email_token(token) is not None:
            return True
        return await self.token_repository.get_email_change_token(token) is not None

    async def confirm_email(self, token: str) -> bool:
        confirm_token = await self.token_repository.get_confirm_email_token(token)
        if not confirm_token:
            return await self._confirm_email_change(token)

        user = await self.user_repository.get_by_id(confirm_token.user_id)
        if not user:
            logger.warning(
                "Email confirmation attempted for missing user: %s",
                confirm_token.user_id,
            )
            raise TokenInvalid("confirm_email:user_not_found")

        await self.user_repository.confirm_email(user)
        await self.token_repository.revoke_confirm_email_tokens(user.id)
        await self._apply_pending_invite(user)
        logger.info("Email confirmed for user: %s", user.id)
        if not user.user_confirmed:
            try:
                await self.mail_template_service.send_to_staff_notification(
                    MailTemplateKey.ACCOUNT_AWAITING_CONFIRMATION,
                    AccountAwaitingConfirmationContext(
                        name=user.display_name,
                        email=user.email,
                        admin_url=frontend_url(STAFF_ACCOUNT_REVIEW_PATH),
                    ),
                )
            except MailUnavailable:
                logger.exception("Staff notification failed for %s", user.id)
        return True

    async def _confirm_email_change(self, token: str) -> bool:
        change_token = await self.token_repository.get_email_change_token(token)
        if not change_token:
            logger.warning("Email confirmation attempted with invalid/expired token")
            raise TokenInvalid("confirm_email")
        user = await self.user_repository.get_by_id(change_token.user_id)
        if user is None or user.pending_email != change_token.new_email:
            raise TokenInvalid("confirm_email:email_change_outdated")
        if await self.user_repository.get_by_email(change_token.new_email):
            raise EmailUsed(f"confirm_email:{change_token.new_email}")
        await self.user_repository.apply_email_change(user, change_token.new_email)
        await self.token_repository.revoke_email_change_tokens(user.id)
        await self.token_repository.revoke_all_refresh_tokens(user.id)
        await self.token_repository.revoke_reset_password_tokens(user.id)
        await self.token_repository.revoke_login_link_tokens(user.id)
        logger.info("Email change confirmed for user %s", user.id)
        return True

    async def _apply_pending_invite(self, user: User) -> None:
        token = user.pending_invite_token
        if token is None:
            return
        try:
            await self.invite_service.join_company(user, token, "confirm_email")
        except AppError as error:
            logger.warning(
                "Pending invite not applied for %s: %s", user.id, error.code
            )
        await self.user_repository.clear_pending_invite(user)

    async def keycloak_callback(self, code: str, code_verifier: str) -> str:
        settings = get_settings()
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "client_id": settings.SIP_AUTH_OIDC_CLIENT_ID,
            "client_secret": settings.SIP_AUTH_OIDC_CLIENT_SECRET.get_secret_value(),
            "redirect_uri": settings.KEYCLOAK_CALLBACK,
        }

        response = await self._token_endpoint(payload)

        if response.status_code != 200:
            raise KeycloakExchangeFailed(f"keycloak_callback:{code}")

        tokens = response.json()
        decoded_token = decode_token(tokens.get("access_token"))
        if not decoded_token:
            raise KeycloakExchangeFailed(f"keycloak_callback:invalid_token:{code}")
        return await self.login_keycloak_user(
            decoded_token, tokens.get("refresh_token")
        )

    async def login_keycloak_user(
        self, decoded_token: dict[str, Any], idp_refresh_token: str | None = None
    ) -> str:
        user = await self.map_keycloak_to_user(decoded_token)
        return await self.token_repository.create_refresh_token(
            user.id, idp_refresh_token=idp_refresh_token
        )

    async def map_keycloak_to_user(self, decoded_token: dict[str, Any]) -> User:
        settings = get_settings()
        if settings.DEBUG and settings.DEBUG_KEYCLOAK_ADMIN:
            keycloak_roles = [settings.ADMIN_GROUP]
        else:
            keycloak_roles = (
                decoded_token.get("resource_access", {})
                .get(get_settings().SIP_AUTH_OIDC_CLIENT_ID, {})
                .get("roles", [])
            )

        admin, roles = await self.map_keycloak_roles(
            keycloak_roles, ["vis-active", "admin"]
        )

        email = decoded_token.get("email")
        sub = decoded_token.get("sub")
        if not isinstance(email, str) or not email.strip():
            raise KeycloakExchangeFailed(f"keycloak:missing_email:{sub}")
        if not isinstance(sub, str) or not sub:
            raise KeycloakExchangeFailed("keycloak:missing_subject")

        if not roles:
            await self._offboard(sub)
            raise NotVisMember(f"keycloak:{sub}")

        first_name, last_name = keycloak_names(decoded_token)

        keycloak_user = User(
            email=email,
            sub=sub,
            user_confirmed=True,
            email_confirmed=True,
            is_admin=admin,
            is_staff=True,
            is_company=False,
            first_name=first_name,
            last_name=last_name,
        )

        db_user = await self.user_repository.get_by_sub(sub)
        if db_user is not None:
            return await self.user_repository.update_keycloak_user(
                db_user, keycloak_user, roles
            )

        email_owner = await self.user_repository.get_by_email(email)
        if email_owner is not None and is_unclaimed_local_account(email_owner):
            logger.info(
                "SSO login replaces unconfirmed local account %s", email_owner.id
            )
            await self.user_repository.delete_user(email_owner)
        elif email_owner is not None:
            if is_local_account(email_owner):
                raise EmailTakenLocally(f"keycloak:{email}")
            raise EmailUsed(f"keycloak:{email}")

        return await self.user_repository.create_user(keycloak_user, roles)

    async def _offboard(self, sub: str) -> None:
        user = await self.user_repository.get_by_sub(sub)
        if user is None:
            return
        await self.user_repository.revoke_privileges(user)
        await self.token_repository.revoke_all_refresh_tokens(user.id)
        logger.warning("SSO user lost the VIS roles and was signed out: %s", user.id)

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
