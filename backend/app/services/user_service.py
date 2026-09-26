import logging
from collections.abc import Sequence
from typing import TypeVar
from uuid import UUID

from app.core.auth_context import require_admin_user, require_staff_user
from app.core.exceptions import (
    CompanyNotFound,
    EmailUsed,
    NotAllowed,
    PhoneNumberInvalid,
    UserLastCompanyMember,
    UserNotFound,
)
from app.core.utils import normalize_email, normalize_phone_number
from app.mail_templates.context import AccountConfirmedContext
from app.mail_templates.keys import MailTemplateKey
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    StaffUserResponse,
    UpdateCompanyUserInput,
    UpdateUserProfileInput,
    UserFilter,
    UserPageResult,
    UserProfileFieldsInput,
)
from app.services.auth_service import AuthService
from app.services.mail_template_service import MailTemplateService

logger = logging.getLogger(__name__)

UpdateInputT = TypeVar("UpdateInputT", bound=UserProfileFieldsInput)
PRIVILEGE_FIELDS = frozenset({"is_staff", "is_admin"})


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: TokenRepository,
        company_repository: CompanyRepository,
        auth_service: AuthService,
        mail_template_service: MailTemplateService,
        current_user: User,
    ) -> None:
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.company_repository = company_repository
        self.auth_service = auth_service
        self.mail_template_service = mail_template_service
        self.current_user = current_user

    async def get_current_user(self) -> User:
        return await self.user_repository.load_user_roles(self.current_user)

    async def get_current_user_profile(self) -> User:
        return await self.user_repository.load_user_company(self.current_user)

    def _with_normalized_phone_number(
        self, update: UpdateInputT, identifier: str
    ) -> UpdateInputT:
        if "phone_number" not in update.model_fields_set:
            return update
        try:
            normalized = normalize_phone_number(update.phone_number)
        except Exception:
            raise PhoneNumberInvalid(identifier)
        return update.model_copy(update={"phone_number": normalized})

    async def update_current_user_profile(self, update: UpdateUserProfileInput) -> User:
        normalized = self._with_normalized_phone_number(
            update, f"update_current_user_profile:{self.current_user.id}"
        )
        updated_user = await self.user_repository.update_user(
            self.current_user, normalized
        )
        logger.info(f"User profile updated: {self.current_user.email}")
        return updated_user

    async def logout_user(self, refresh_token: str | None) -> None:
        if refresh_token:
            await self.token_repository.revoke_refresh_token(
                self.current_user.id, refresh_token
            )

    async def list_users(
        self, query: str | None, user_filter: UserFilter, page: int, page_size: int
    ) -> UserPageResult:
        require_staff_user(self.current_user)
        total = await self.user_repository.count_users_matching(query, user_filter)
        users = await self.user_repository.search_users(
            query, user_filter, (page - 1) * page_size, page_size
        )
        return UserPageResult(
            items=[StaffUserResponse.model_validate(user) for user in users],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_user(self, user_id: UUID) -> User:
        require_staff_user(self.current_user)
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(f"get_user:{user_id}")
        return await self.user_repository.load_user_company(user)

    async def get_unconfirmed_users(self) -> Sequence[User]:
        require_staff_user(self.current_user)
        return await self.user_repository.get_unconfirmed_users()

    async def confirm_user(self, user_id: UUID) -> User:
        require_staff_user(self.current_user)
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"Confirm user failed - user not found: {user_id}")
            raise UserNotFound(f"confirm_user:{user_id}")

        was_confirmed = user.user_confirmed
        result = await self.user_repository.confirm_user(user)
        if not was_confirmed:
            await self._send_account_confirmed(result)
        logger.info(f"User confirmed by staff {self.current_user.email}: {user.email}")
        return result

    async def _send_account_confirmed(self, user: User) -> None:
        if not user.is_company:
            return
        try:
            login_url = await self.auth_service.create_login_link(user, "/")
            await self.mail_template_service.send(
                MailTemplateKey.ACCOUNT_CONFIRMED,
                [user.email],
                AccountConfirmedContext(name=user.display_name, login_url=login_url),
            )
        except Exception:
            logger.exception(f"Account confirmed mail failed for {user.email}")

    async def get_company_users(self) -> Sequence[User]:
        require_staff_user(self.current_user)
        return await self.user_repository.get_company_users()

    async def get_admins(self) -> Sequence[User]:
        require_staff_user(self.current_user)
        return await self.user_repository.get_admins()

    async def get_staff(self) -> Sequence[User]:
        require_staff_user(self.current_user)
        return await self.user_repository.get_staff()

    async def resend_confirmation_mail(self, user_id: UUID) -> None:
        require_staff_user(self.current_user)
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(f"resend_confirmation_mail:{user_id}")
        await self.auth_service.send_confirm_email(user)
        logger.info(
            f"Confirmation mail resent by staff {self.current_user.email}: {user.email}"
        )

    async def update_company_user(
        self, user_id: UUID, update: UpdateCompanyUserInput
    ) -> User:
        require_staff_user(self.current_user)
        if PRIVILEGE_FIELDS & update.model_fields_set:
            require_admin_user(self.current_user)
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(f"update_company_user:{user_id}")
        if user.is_admin or user.is_staff:
            require_admin_user(self.current_user)
        normalized = self._with_normalized_phone_number(
            update, f"update_company_user:{user_id}"
        )

        new_email = self._changed_email(user, normalized.email)
        if new_email is not None and await self.user_repository.get_by_email(new_email):
            raise EmailUsed(f"update_company_user:{new_email}")
        await self._check_company_reassignment(user, normalized)

        was_confirmed = user.user_confirmed
        updated_user = await self.user_repository.update_user(user, normalized)
        if new_email is not None:
            await self._revoke_credentials_after_email_change(updated_user)
        if updated_user.user_confirmed and not was_confirmed:
            await self._send_account_confirmed(updated_user)
        return updated_user

    async def _check_company_reassignment(
        self, user: User, update: UpdateCompanyUserInput
    ) -> None:
        if "company_id" not in update.model_fields_set:
            return
        if update.company_id == user.company_id:
            return
        if update.company_id is not None:
            company = await self.company_repository.get_by_id(update.company_id)
            if company is None:
                raise CompanyNotFound(f"update_company_user:{update.company_id}")
        if user.company_id is not None:
            await self._ensure_company_keeps_a_member(
                user.company_id, "update_company_user"
            )

    async def _ensure_company_keeps_a_member(
        self, company_id: UUID, action: str
    ) -> None:
        if await self.company_repository.is_last_member_of_booked_company(company_id):
            raise UserLastCompanyMember(f"{action}:{company_id}")

    def _changed_email(self, user: User, email: str | None) -> str | None:
        if email is None:
            return None
        normalized = normalize_email(email)
        return normalized if normalized != user.email else None

    async def _revoke_credentials_after_email_change(self, user: User) -> None:
        await self.token_repository.revoke_all_refresh_tokens(user.id)
        await self.token_repository.revoke_reset_password_tokens(user.id)
        await self.token_repository.revoke_login_link_tokens(user.id)
        await self.auth_service.send_confirm_email(user)
        logger.info(f"Email changed by admin {self.current_user.email}: {user.email}")

    async def delete_user(self, user_id: UUID) -> None:
        require_staff_user(self.current_user)
        if user_id == self.current_user.id:
            logger.warning(f"Delete user failed - user deletes itself: {user_id}")
            raise NotAllowed(f"delete_user:self:{user_id}")
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"Delete user failed - user not found: {user_id}")
            raise UserNotFound(f"delete_user:{user_id}")
        if user.is_admin or user.is_staff:
            require_admin_user(self.current_user)
        if user.company_id is not None:
            await self._ensure_company_keeps_a_member(user.company_id, "delete_user")

        await self.user_repository.delete_user(user)
        logger.info(f"User deleted by staff {self.current_user.email}: {user.email}")
