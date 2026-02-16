from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from app.core.decorators import require_confirmed_company
from app.core.exceptions import TokenInvalid
from app.core.utils import hash_str
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.mail_service import MailService

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
        
        await self.mail_service.send_confirm_email_mail(self.current_user.email, raw_token)

    async def create_confirm_email_token(self):
        raw_token = secrets.token_urlsafe(32)
        hashed_token = hash_str(raw_token)

        expire = datetime.now(timezone.utc) + CONFIRM_EMAIL_TOKEN_EXPIRE

        await self.user_repository.save_confirm_email_token(
            hashed_token, self.current_user, expire
        )

        return raw_token
    
    async def confirm_email(self, token: str):
        token_is_valid = await self.user_repository.validate_confirm_email_token(self.current_user, hash_str(token))
        
        if not token_is_valid:
            raise TokenInvalid("")
        
        await self.user_repository.confirm_email(self.current_user)
        await self.user_repository.revoke_confirm_email_tokens(self.current_user)
        return True
        
    @require_confirmed_company
    async def get_current_user(self):
        return self.current_user
    
    async def logout_user(self, refresh_token: str):
        await self.user_repository.revoke_refresh_token(self.current_user, hash_str(refresh_token))
        
        
