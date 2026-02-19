from datetime import datetime, timedelta, timezone
import secrets
import logging
from uuid import UUID
from app.core.decorators import require_admin, require_staff
from app.core.exceptions import NotAllowed, TokenInvalid, UserNotFound
from app.core.utils import hash_str
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.mail_service import MailService

logger = logging.getLogger(__name__)

CONFIRM_EMAIL_TOKEN_EXPIRE = timedelta(days=3)


class UserService:

    def __init__(
        self,
        user_repository: UserRepository,
        mail_service: MailService,
        current_user: User,
    ):
        self.user_repository = user_repository
        self.mail_service = mail_service
        self.current_user = current_user

    async def send_confirmation_mail(self):
        if self.current_user.email_confirmed:
            return None

        await self.user_repository.revoke_confirm_email_tokens(self.current_user)
        raw_token = await self.create_confirm_email_token()

        await self.mail_service.send_confirm_email_mail(
            self.current_user.email, raw_token
        )

    async def create_confirm_email_token(self):
        raw_token = secrets.token_urlsafe(32)
        hashed_token = hash_str(raw_token)

        expire = datetime.now(timezone.utc) + CONFIRM_EMAIL_TOKEN_EXPIRE

        await self.user_repository.save_confirm_email_token(
            hashed_token, self.current_user, expire
        )

        return raw_token

    async def confirm_email(self, token: str):
        token_is_valid = await self.user_repository.validate_confirm_email_token(
            self.current_user, hash_str(token)
        )

        if not token_is_valid:
            logger.warning(f"Email confirmation failed for user: {self.current_user.email}")
            raise TokenInvalid(f"confirm_email:{self.current_user.id}")

        await self.user_repository.confirm_email(self.current_user)
        await self.user_repository.revoke_confirm_email_tokens(self.current_user)
        logger.info(f"Email confirmed for user: {self.current_user.email}")
        return True

    async def validate_confirm_email_token(self, token: str) -> bool:
        return await self.user_repository.validate_confirm_email_token(
            self.current_user,
            hash_str(token),
        )

    async def get_current_user(self):
        return await self.user_repository.load_user_company(self.current_user)

    async def logout_user(self, refresh_token: str):
        await self.user_repository.revoke_refresh_token(
            self.current_user, hash_str(refresh_token)
        )

    @require_staff
    async def get_unconfirmed_users(self):
        return await self.user_repository.get_unconfirmed_users()

    @require_staff
    async def confirm_user(self, user_id: UUID):
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"Confirm user failed - user not found: {user_id}")
            raise UserNotFound(f"confirm_user:{user_id}")
        
        result = await self.user_repository.confirm_user(user)
        logger.info(f"User confirmed by staff {self.current_user.email}: {user.email}")
        return result

    @require_staff
    async def get_company_users(self):
        return await self.user_repository.get_company_users()

    @require_staff
    async def get_admins(self):
        return await self.user_repository.get_admins()

    @require_staff
    async def get_staff(self):
        return await self.user_repository.get_staff()
    
    @require_admin
    async def delete_user(self, user_id: UUID):
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"Delete user failed - user not found: {user_id}")
            raise UserNotFound(f"delete_user:{user_id}")
        if (user.is_admin or user.is_staff):
            logger.warning(f"Delete user failed - user is admin or staff: {user_id}")
            raise NotAllowed(f"delete_user:{user_id}")
        
        await self.user_repository.delete_user(user)
        logger.info(f"User deleted by admin {self.current_user.email}: {user.email}")
