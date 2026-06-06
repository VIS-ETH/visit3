import logging
from collections.abc import Sequence
from uuid import UUID

from app.core.auth_context import require_admin_user, require_staff_user
from app.core.exceptions import (
    NotAllowed,
    PhoneNumberInvalid,
    UserNotFound,
)
from app.core.utils import normalize_phone_number
from app.models.user import User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: TokenRepository,
        current_user: User,
    ) -> None:
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.current_user = current_user

    async def get_current_user(self) -> User:
        return await self.user_repository.load_user_roles(self.current_user)

    async def get_current_user_profile(self) -> User:
        return await self.user_repository.load_user_company(self.current_user)

    async def update_current_user_profile(
        self,
        first_name: str | None,
        last_name: str | None,
        phone_number: str | None,
    ) -> User:
        try:
            phone_number = normalize_phone_number(phone_number)
        except Exception:
            raise PhoneNumberInvalid(
                f"update_current_user_profile:{self.current_user.id}"
            )
        updated_user = await self.user_repository.update_company_user(
            self.current_user,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
        logger.info(f"User profile updated: {self.current_user.email}")
        return updated_user

    async def logout_user(self, refresh_token: str | None) -> None:
        if refresh_token:
            await self.token_repository.revoke_refresh_token(
                self.current_user.id, refresh_token
            )

    async def get_unconfirmed_users(self) -> Sequence[User]:
        require_staff_user(self.current_user)
        return await self.user_repository.get_unconfirmed_users()

    async def confirm_user(self, user_id: UUID) -> User:
        require_staff_user(self.current_user)
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"Confirm user failed - user not found: {user_id}")
            raise UserNotFound(f"confirm_user:{user_id}")

        result = await self.user_repository.confirm_user(user)
        logger.info(f"User confirmed by staff {self.current_user.email}: {user.email}")
        return result

    async def get_company_users(self) -> Sequence[User]:
        require_staff_user(self.current_user)
        return await self.user_repository.get_company_users()

    async def get_admins(self) -> Sequence[User]:
        require_staff_user(self.current_user)
        return await self.user_repository.get_admins()

    async def get_staff(self) -> Sequence[User]:
        require_staff_user(self.current_user)
        return await self.user_repository.get_staff()

    async def update_company_user(
        self,
        user_id: UUID,
        email: str | None,
        first_name: str | None,
        last_name: str | None,
        phone_number: str | None,
        company_id: UUID | None,
    ) -> User:
        require_admin_user(self.current_user)
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(f"update_company_user:{user_id}")
        try:
            phone_number = normalize_phone_number(phone_number)
        except Exception:
            raise PhoneNumberInvalid(f"update_company_user:{user_id}")
        return await self.user_repository.update_company_user(
            user,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            company_id=company_id,
        )

    async def delete_user(self, user_id: UUID) -> None:
        require_admin_user(self.current_user)
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"Delete user failed - user not found: {user_id}")
            raise UserNotFound(f"delete_user:{user_id}")
        if user.is_admin or user.is_staff:
            logger.warning(f"Delete user failed - user is admin or staff: {user_id}")
            raise NotAllowed(f"delete_user:{user_id}")

        await self.user_repository.delete_user(user)
        logger.info(f"User deleted by admin {self.current_user.email}: {user.email}")
