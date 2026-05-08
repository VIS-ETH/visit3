import logging
import secrets
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.decorators import require_admin, require_confirmed_company, require_staff
from app.core.exceptions import (
    CompanyNotFound,
    CompanyUserNotFound,
    InviteExpired,
    InviteNotFound,
    NotAllowed,
    UserNotFound,
)
from app.core.utils import normalize_email
from app.models.company import Company, CompanyInvite
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import (
    CompanyAssignedUserResult,
    CompanyWithUsersResult,
    InviteInfoResult,
    KpCompanyProfileResult,
)
from app.services.mail_service import MailService

logger = logging.getLogger(__name__)

INVITE_EXPIRE = timedelta(days=7)


class CompanyService:
    def __init__(
        self,
        company_repository: CompanyRepository,
        mail_service: MailService,
        current_user: User,
    ) -> None:
        self.company_repository = company_repository
        self.mail_service = mail_service
        self.current_user = current_user

    @require_staff
    async def get_company_users(self, company_id: UUID) -> Sequence[User]:
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"company_users:{company_id}")
        return await self.company_repository.get_users(company)

    @require_staff
    async def get_companies_with_users(self) -> Sequence[CompanyWithUsersResult]:
        companies = await self.company_repository.get_companies_with_users()
        return [
            CompanyWithUsersResult(
                id=company.id,
                name=company.name,
                users=[
                    CompanyAssignedUserResult(
                        id=user.id,
                        email=user.email,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        phone_number=user.phone_number,
                        user_confirmed=user.user_confirmed,
                        email_confirmed=user.email_confirmed,
                    )
                    for user in company.users
                ],
            )
            for company in companies
        ]

    @require_admin
    async def delete_company_with_users(self, company_id: UUID) -> None:
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"delete_company_with_users:{company_id}")
        await self.company_repository.delete_company_with_users(company)

    @require_admin
    async def delete_company_keep_users(self, company_id: UUID) -> None:
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"delete_company_keep_users:{company_id}")
        await self.company_repository.delete_company_keep_users(company)

    @require_admin
    async def remove_company_user(self, company_id: UUID, user_id: UUID) -> None:
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"remove_company_user:{company_id}")
        user = await self.company_repository.get_company_user_by_id(user_id)
        if not user:
            raise UserNotFound(f"remove_company_user:{user_id}")
        if user.company_id != company.id:
            raise CompanyUserNotFound(f"remove_company_user:{company_id}:{user_id}")

        await self.company_repository.remove_user_from_company(user, company)
        logger.info(
            f"Company user removed by admin {self.current_user.email}: "
            f"{user.email} from {company.name}"
        )

    async def setup_company(self, name: str) -> Company:
        if not (
            self.current_user.email_confirmed
            and self.current_user.user_confirmed
            and self.current_user.is_company
        ):
            raise NotAllowed(f"setup_company:not_confirmed:{self.current_user.id}")
        if self.current_user.company_id:
            raise NotAllowed(f"setup_company:already_in_company:{self.current_user.id}")
        normalized = name.strip()
        existing = await self.company_repository.get_by_name(normalized)
        if existing:
            raise NotAllowed(f"setup_company:name_taken:{normalized}")
        company = await self.company_repository.create_company(normalized)
        await self.company_repository.assign_user(self.current_user, company.id)
        logger.info(
            f"Company created and joined: {self.current_user.email} -> {company.name}"
        )
        return company

    @require_confirmed_company
    async def get_my_members(self) -> Sequence[User]:
        assert self.current_user.company_id is not None
        company = await self.company_repository.get_by_id(self.current_user.company_id)
        if company is None:
            raise CompanyNotFound(f"my_members:{self.current_user.company_id}")
        return await self.company_repository.get_users(company)

    @require_confirmed_company
    async def create_invite(self, email: str) -> CompanyInvite:
        assert self.current_user.company_id is not None
        normalized = normalize_email(email)
        company = await self.company_repository.get_by_id(self.current_user.company_id)
        if not company:
            raise CompanyNotFound(f"create_invite:{self.current_user.company_id}")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + INVITE_EXPIRE
        invite = await self.company_repository.create_invite(
            token=token,
            company_id=company.id,
            invited_email=normalized,
            expires_at=expires_at,
        )
        await self.mail_service.send_company_invite_mail(
            normalized, company.name, token
        )
        logger.info(
            f"Invite sent by {self.current_user.email} to {normalized} for {company.name}"
        )
        return invite

    async def get_invite_info(self, token: str) -> InviteInfoResult:
        invite = await self.company_repository.get_invite_by_token(token)
        if not invite or invite.is_used:
            raise InviteNotFound(f"get_invite_info:{token}")
        if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise InviteExpired(f"get_invite_info:{token}")
        company = await self.company_repository.get_by_id(invite.company_id)
        if not company:
            raise CompanyNotFound(f"get_invite_info:{invite.company_id}")
        return InviteInfoResult(company_name=company.name)

    @require_confirmed_company
    async def accept_invite(self, token: str) -> User:
        if not (self.current_user.email_confirmed and self.current_user.user_confirmed):
            raise NotAllowed(f"accept_invite:not_confirmed:{self.current_user.id}")
        if self.current_user.company_id:
            raise NotAllowed(f"accept_invite:already_in_company:{self.current_user.id}")
        invite = await self.company_repository.get_invite_by_token(token)
        if not invite or invite.is_used:
            raise InviteNotFound(f"accept_invite:{token}")
        if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise InviteExpired(f"accept_invite:{token}")
        if normalize_email(invite.invited_email) != self.current_user.email:
            raise NotAllowed(f"accept_invite:email_mismatch:{self.current_user.email}")
        await self.company_repository.mark_invite_used(invite)
        user = await self.company_repository.assign_user(
            self.current_user, invite.company_id
        )
        logger.info(
            f"Invite accepted: {self.current_user.email} joined company {invite.company_id}"
        )
        return user

    @require_confirmed_company
    async def update_company_name(self, name: str) -> Company:
        if not self.current_user.company_id:
            logger.warning(
                f"Update company name failed - user has no company: {self.current_user.email}"
            )
            raise NotAllowed(f"update_company_name:{self.current_user.id}")

        company = await self.company_repository.get_by_id(self.current_user.company_id)
        if not company:
            logger.warning(
                f"Update company name failed - company not found: {self.current_user.company_id}"
            )
            raise CompanyNotFound(f"update_company_name:{self.current_user.company_id}")

        updated_company = await self.company_repository.update_company_name(
            company, name
        )
        logger.info(
            f"Company name updated by {self.current_user.email}: {company.name} -> {name}"
        )
        return updated_company

    @require_confirmed_company
    async def get_my_kp_profile(self) -> KpCompanyProfileResult | None:
        assert self.current_user.company_id is not None
        profile = await self.company_repository.get_kp_profile(
            self.current_user.company_id
        )
        if profile is None:
            return None
        return KpCompanyProfileResult(
            id=profile.id,
            company_id=profile.company_id,
            invoice_address=profile.invoice_address,
            shipping_address=profile.shipping_address,
            contact_email=profile.contact_email,
            kp_contact_user_id=profile.kp_contact_user_id,
        )

    @require_confirmed_company
    async def update_my_kp_profile(
        self,
        invoice_address: str,
        shipping_address: str,
        contact_email: str | None,
        kp_contact_user_id: UUID | None,
    ) -> KpCompanyProfileResult:
        assert self.current_user.company_id is not None
        if kp_contact_user_id is not None:
            user = next(
                (
                    member
                    for member in await self.get_my_members()
                    if member.id == kp_contact_user_id
                ),
                None,
            )
            if user is None:
                raise CompanyUserNotFound(
                    f"update_my_kp_profile:user_not_in_company:{kp_contact_user_id}"
                )

        profile = await self.company_repository.upsert_kp_profile(
            company_id=self.current_user.company_id,
            invoice_address=invoice_address.strip(),
            shipping_address=shipping_address.strip(),
            contact_email=contact_email,
            kp_contact_user_id=kp_contact_user_id,
        )
        return KpCompanyProfileResult(
            id=profile.id,
            company_id=profile.company_id,
            invoice_address=profile.invoice_address,
            shipping_address=profile.shipping_address,
            contact_email=profile.contact_email,
            kp_contact_user_id=profile.kp_contact_user_id,
        )
