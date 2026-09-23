import logging
from datetime import datetime, timezone

from app.core.exceptions import (
    CompanyNotFound,
    InviteEmailMismatch,
    InviteExpired,
    InviteNotFound,
)
from app.core.utils import normalize_email
from app.models.company import CompanyInvite
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import InviteInfoResult

logger = logging.getLogger(__name__)


class InviteService:
    def __init__(self, company_repository: CompanyRepository) -> None:
        self.company_repository = company_repository

    async def load_open_invite(self, token: str, action: str) -> CompanyInvite:
        invite = await self.company_repository.get_invite_by_token(token)
        if not invite or invite.is_used:
            raise InviteNotFound(f"{action}:{token}")
        if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise InviteExpired(f"{action}:{token}")
        return invite

    def ensure_email_matches(
        self, invite: CompanyInvite, email: str, action: str
    ) -> None:
        if normalize_email(invite.invited_email) != normalize_email(email):
            raise InviteEmailMismatch(f"{action}:{email}")

    async def get_invite_info(self, token: str) -> InviteInfoResult:
        invite = await self.load_open_invite(token, "get_invite_info")
        company = await self.company_repository.get_by_id(invite.company_id)
        if not company:
            raise CompanyNotFound(f"get_invite_info:{invite.company_id}")
        account = await self.company_repository.get_user_by_email(invite.invited_email)
        return InviteInfoResult(
            company_name=company.name, account_exists=account is not None
        )

    async def join_company(self, user: User, token: str, action: str) -> User:
        invite = await self.load_open_invite(token, action)
        self.ensure_email_matches(invite, user.email, action)
        await self.company_repository.mark_invite_used(invite)
        joined = await self.company_repository.assign_user(user, invite.company_id)
        logger.info(f"Invite accepted: {user.email} joined company {invite.company_id}")
        return joined
