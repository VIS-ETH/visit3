import logging
import secrets
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import UUID, uuid4

from app.core.auth_context import (
    require_admin_user,
    require_assigned_company_user,
    require_company_profile_user,
    require_confirmed_company_user,
    require_staff_user,
)
from app.core.config import get_settings
from app.core.exceptions import (
    CompanyHasUpcomingBookings,
    CompanyInvitePending,
    CompanyNotFound,
    CompanyUserNotFound,
    IndustryNotFound,
    NotAllowed,
    UserAlreadyInCompany,
    UserLastCompanyMember,
    UserNotFound,
)
from app.core.utils import normalize_email
from app.mail_templates.context import CompanyInviteContext
from app.mail_templates.keys import MailTemplateKey
from app.models.company import (
    MANDATORY_PROFILE_FIELDS,
    Company,
    CompanyInvite,
    KpCompanyProfile,
)
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import (
    CompanyAssignedUserResult,
    CompanyListResult,
    CompanyMemberResult,
    CompanyPageResult,
    CompanyProfileResult,
    CompanyWithUsersResult,
    MyCompanyResult,
    UpdateCompanyProfileInput,
)
from app.schemas.industry import IndustryResult
from app.services.invite_service import InviteService
from app.services.mail_template_service import MailTemplateService
from app.services.storage_service import StorageService, UploadKind, UploadStream

logger = logging.getLogger(__name__)

INVITE_EXPIRE = timedelta(days=7)
LOGO_CONTEXT = "company_profile_logo"
LOGO_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}


def member_result(user: User) -> CompanyMemberResult:
    return CompanyMemberResult(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
    )


class CompanyService:
    def __init__(
        self,
        company_repository: CompanyRepository,
        mail_template_service: MailTemplateService,
        storage_service: StorageService,
        current_user: User,
    ) -> None:
        self.company_repository = company_repository
        self.mail_template_service = mail_template_service
        self.storage_service = storage_service
        self.current_user = current_user
        self.invite_service = InviteService(company_repository)

    async def get_company_users(self, company_id: UUID) -> Sequence[User]:
        require_staff_user(self.current_user)
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"company_users:{company_id}")
        return await self.company_repository.get_users(company)

    async def get_company_with_users(self, company_id: UUID) -> CompanyWithUsersResult:
        require_staff_user(self.current_user)
        company = await self.company_repository.get_company_with_users(company_id)
        if not company:
            raise CompanyNotFound(f"company_with_users:{company_id}")
        return self._company_with_users_result(company)

    async def get_companies(self) -> Sequence[CompanyListResult]:
        require_staff_user(self.current_user)
        return await self._company_overviews()

    async def search_companies(
        self, query: str | None, page: int, page_size: int
    ) -> CompanyPageResult:
        require_staff_user(self.current_user)
        total = await self.company_repository.count_companies(query)
        items = await self._company_overviews(query, (page - 1) * page_size, page_size)
        return CompanyPageResult(
            items=list(items), total=total, page=page, page_size=page_size
        )

    async def _company_overviews(
        self,
        query: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Sequence[CompanyListResult]:
        companies = await self.company_repository.get_company_overviews(
            query, offset, limit
        )
        return [
            CompanyListResult(
                id=company_id,
                name=name,
                users_count=users_count,
                bookings_count=bookings_count,
            )
            for company_id, name, users_count, bookings_count in companies
        ]

    def _company_with_users_result(self, company: Company) -> CompanyWithUsersResult:
        return CompanyWithUsersResult(
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

    async def _get_deletable_company(self, company_id: UUID, action: str) -> Company:
        require_admin_user(self.current_user)
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"{action}:{company_id}")
        if await self.company_repository.has_bookings_for_upcoming_events(company.id):
            raise CompanyHasUpcomingBookings(f"{action}:{company_id}")
        return company

    async def delete_company_with_users(self, company_id: UUID) -> None:
        company = await self._get_deletable_company(
            company_id, "delete_company_with_users"
        )
        await self.company_repository.delete_company_with_users(company)

    async def delete_company_keep_users(self, company_id: UUID) -> None:
        company = await self._get_deletable_company(
            company_id, "delete_company_keep_users"
        )
        await self.company_repository.delete_company_keep_users(company)

    async def remove_company_user(self, company_id: UUID, user_id: UUID) -> None:
        require_staff_user(self.current_user)
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"remove_company_user:{company_id}")
        user = await self.company_repository.get_company_user_by_id(user_id)
        if not user:
            raise UserNotFound(f"remove_company_user:{user_id}")
        if user.company_id != company.id:
            raise CompanyUserNotFound(f"remove_company_user:{company_id}:{user_id}")
        if await self.company_repository.is_last_member_of_booked_company(company.id):
            raise UserLastCompanyMember(f"remove_company_user:{company_id}")

        await self.company_repository.remove_user_from_company(user, company)
        logger.info(
            f"Company user removed by staff {self.current_user.email}: "
            f"{user.email} from {company.name}"
        )

    async def add_company_user(self, company_id: UUID, user_id: UUID) -> User:
        require_staff_user(self.current_user)
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"add_company_user:{company_id}")
        user = await self.company_repository.get_company_user_by_id(user_id)
        if not user:
            raise UserNotFound(f"add_company_user:{user_id}")
        if not user.is_company:
            raise NotAllowed(f"add_company_user:not_a_company_user:{user_id}")
        if user.company_id is not None:
            raise UserAlreadyInCompany(f"add_company_user:{company_id}:{user_id}")

        joined = await self.company_repository.assign_user(user, company.id)
        logger.info(
            f"Company user added by staff {self.current_user.email}: "
            f"{user.email} to {company.name}"
        )
        return joined

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
        if normalized == "":
            raise NotAllowed("setup_company:empty_name")
        existing = await self.company_repository.get_by_name(normalized)
        if existing:
            raise NotAllowed(f"setup_company:name_taken:{normalized}")
        company = await self.company_repository.create_company(normalized)
        await self.company_repository.assign_user(self.current_user, company.id)
        logger.info(
            f"Company created and joined: {self.current_user.email} -> {company.name}"
        )
        return company

    async def get_my_members(self) -> Sequence[User]:
        company_user = require_assigned_company_user(self.current_user)
        company = await self.company_repository.get_by_id(company_user.company_id)
        if company is None:
            raise CompanyNotFound(f"my_members:{company_user.company_id}")
        return await self.company_repository.get_users(company)

    async def create_invite(self, email: str) -> CompanyInvite:
        company_user = require_assigned_company_user(self.current_user)
        normalized = normalize_email(email)
        company = await self.company_repository.get_by_id(company_user.company_id)
        if not company:
            raise CompanyNotFound(f"create_invite:{company_user.company_id}")
        pending = await self.company_repository.get_pending_invite(
            company.id, normalized
        )
        if pending is not None:
            raise CompanyInvitePending(f"create_invite:{company.id}:{normalized}")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + INVITE_EXPIRE
        invite = await self.company_repository.create_invite(
            token=token,
            company_id=company.id,
            invited_email=normalized,
            expires_at=expires_at,
        )
        await self.mail_template_service.send(
            MailTemplateKey.COMPANY_INVITE,
            [normalized],
            CompanyInviteContext(
                company_name=company.name,
                invite_url=(
                    f"{get_settings().VISIT_FRONTEND_SERVER_URL}/company/join/{token}"
                    f"?email={quote(normalized, safe='')}"
                ),
            ),
        )
        logger.info(
            f"Invite sent by {self.current_user.email} to {normalized} for {company.name}"
        )
        return invite

    async def accept_invite(self, token: str) -> User:
        require_confirmed_company_user(self.current_user)
        if self.current_user.company_id:
            raise NotAllowed(f"accept_invite:already_in_company:{self.current_user.id}")
        return await self.invite_service.join_company(
            self.current_user, token, "accept_invite"
        )

    async def update_company_name(self, name: str) -> Company:
        company_user = require_assigned_company_user(self.current_user)
        company = await self.company_repository.get_by_id(company_user.company_id)
        if not company:
            logger.warning(
                f"Update company name failed - company not found: {company_user.company_id}"
            )
            raise CompanyNotFound(f"update_company_name:{company_user.company_id}")
        return await self._rename_company(company, name)

    async def update_company(self, company_id: UUID, name: str) -> Company:
        require_staff_user(self.current_user)
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"update_company:{company_id}")
        return await self._rename_company(company, name)

    async def _rename_company(self, company: Company, name: str) -> Company:
        normalized = name.strip()
        if normalized == "":
            raise NotAllowed(f"rename_company:empty_name:{company.id}")
        existing = await self.company_repository.get_by_name(normalized)
        if existing is not None and existing.id != company.id:
            raise NotAllowed(f"rename_company:name_taken:{normalized}")

        updated_company = await self.company_repository.update_company_name(
            company, normalized
        )
        logger.info(
            f"Company name updated by {self.current_user.email}: "
            f"{company.name} -> {normalized}"
        )
        return updated_company

    async def get_my_company(self) -> MyCompanyResult:
        company_user = require_company_profile_user(self.current_user)
        company = await self.company_repository.get_by_id(company_user.company_id)
        if company is None:
            raise CompanyNotFound(f"my_company:{company_user.company_id}")
        missing = await self._missing_profile_fields(company.id)
        return MyCompanyResult(
            id=company.id,
            name=company.name,
            profile_complete=not missing,
            missing_profile_fields=missing,
        )

    async def _missing_profile_fields(self, company_id: UUID) -> list[str]:
        profile = await self.company_repository.get_kp_profile(company_id)
        if profile is None:
            return list(MANDATORY_PROFILE_FIELDS)
        return profile.missing_profile_fields()

    async def _profile_result(
        self, company_id: UUID, stored_profile: KpCompanyProfile | None
    ) -> CompanyProfileResult:
        profile = stored_profile or KpCompanyProfile(company_id=company_id)
        missing = profile.missing_profile_fields()
        return CompanyProfileResult(
            id=stored_profile.id if stored_profile is not None else None,
            company_id=company_id,
            description=profile.description,
            website=profile.website,
            logo_url=await self._logo_url(profile),
            brand_name=profile.brand_name,
            general_email=profile.general_email,
            general_phone=profile.general_phone,
            places_of_work=profile.places_of_work,
            employee_count_switzerland=profile.employee_count_switzerland,
            employee_count_worldwide=profile.employee_count_worldwide,
            offers_internships=profile.offers_internships,
            offers_part_time=profile.offers_part_time,
            offers_theses=profile.offers_theses,
            offers_graduate_positions=profile.offers_graduate_positions,
            languages=profile.languages,
            billing_company_name=profile.billing_company_name,
            billing_street=profile.billing_street,
            billing_house_number=profile.billing_house_number,
            billing_postal_code=profile.billing_postal_code,
            billing_city=profile.billing_city,
            billing_country=profile.billing_country,
            billing_vat_number=profile.billing_vat_number,
            billing_email=profile.billing_email,
            shipping_address=profile.shipping_address,
            kp_contact_user_id=profile.kp_contact_user_id,
            kp_contact_user=member_result(profile.kp_contact_user)
            if profile.kp_contact_user is not None
            else None,
            industries=[
                IndustryResult(id=link.industry.id, name=link.industry.name)
                for link in profile.industry_links
            ],
            profile_completed_at=profile.profile_completed_at,
            profile_complete=not missing,
            missing_profile_fields=missing,
        )

    async def _logo_url(self, profile: KpCompanyProfile) -> str | None:
        stored_file = profile.logo_stored_file
        if stored_file is None:
            return None
        return await self.storage_service.generate_download_url(
            stored_file.storage_key, stored_file.original_filename
        )

    async def _get_or_create_profile(self, company_id: UUID) -> KpCompanyProfile:
        profile = await self.company_repository.get_kp_profile(company_id)
        if profile is not None:
            return profile
        return await self.company_repository.upsert_kp_profile(
            company_id, UpdateCompanyProfileInput()
        )

    async def _ensure_company_exists(self, company_id: UUID, action: str) -> Company:
        company = await self.company_repository.get_by_id(company_id)
        if company is None:
            raise CompanyNotFound(f"{action}:{company_id}")
        return company

    async def _validate_profile_input(
        self, company_id: UUID, profile_input: UpdateCompanyProfileInput
    ) -> None:
        if profile_input.kp_contact_user_id is not None:
            company = await self._ensure_company_exists(
                company_id, "update_company_profile"
            )
            members = await self.company_repository.get_users(company)
            if all(member.id != profile_input.kp_contact_user_id for member in members):
                raise CompanyUserNotFound(
                    "update_company_profile:user_not_in_company:"
                    f"{profile_input.kp_contact_user_id}"
                )
        industry_ids = list(dict.fromkeys(profile_input.industry_ids))
        if not industry_ids:
            return
        industries = await self.company_repository.get_industries_by_ids(industry_ids)
        found = {industry.id for industry in industries}
        for industry_id in industry_ids:
            if industry_id not in found:
                raise IndustryNotFound(
                    f"update_company_profile:industry_not_found:{industry_id}"
                )

    async def get_my_profile(self) -> CompanyProfileResult:
        company_user = require_company_profile_user(self.current_user)
        profile = await self.company_repository.get_kp_profile(company_user.company_id)
        return await self._profile_result(company_user.company_id, profile)

    async def update_my_profile(
        self, profile_input: UpdateCompanyProfileInput
    ) -> CompanyProfileResult:
        company_user = require_company_profile_user(self.current_user)
        await self._validate_profile_input(company_user.company_id, profile_input)
        profile = await self.company_repository.upsert_kp_profile(
            company_user.company_id, profile_input
        )
        return await self._profile_result(company_user.company_id, profile)

    async def get_company_profile(self, company_id: UUID) -> CompanyProfileResult:
        require_staff_user(self.current_user)
        await self._ensure_company_exists(company_id, "company_profile")
        profile = await self.company_repository.get_kp_profile(company_id)
        return await self._profile_result(company_id, profile)

    async def update_company_profile(
        self, company_id: UUID, profile_input: UpdateCompanyProfileInput
    ) -> CompanyProfileResult:
        require_staff_user(self.current_user)
        await self._ensure_company_exists(company_id, "company_profile")
        await self._validate_profile_input(company_id, profile_input)
        profile = await self.company_repository.upsert_kp_profile(
            company_id, profile_input
        )
        return await self._profile_result(company_id, profile)

    async def upload_my_profile_logo(
        self,
        filename: str,
        upload: UploadStream,
        content_length: int | None,
        content_type: str | None,
    ) -> CompanyProfileResult:
        company_user = require_company_profile_user(self.current_user)
        return await self._upload_profile_logo(
            company_user.company_id, filename, upload, content_length, content_type
        )

    async def upload_company_profile_logo(
        self,
        company_id: UUID,
        filename: str,
        upload: UploadStream,
        content_length: int | None,
        content_type: str | None,
    ) -> CompanyProfileResult:
        require_staff_user(self.current_user)
        await self._ensure_company_exists(company_id, "company_profile_logo")
        return await self._upload_profile_logo(
            company_id, filename, upload, content_length, content_type
        )

    async def _upload_profile_logo(
        self,
        company_id: UUID,
        filename: str,
        upload: UploadStream,
        content_length: int | None,
        content_type: str | None,
    ) -> CompanyProfileResult:
        profile = await self._get_or_create_profile(company_id)
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=UploadKind.IMAGE,
            error_context=LOGO_CONTEXT,
        )
        mime_type = self.storage_service.validate_image_file(
            filename,
            content,
            content_type,
            error_context=LOGO_CONTEXT,
            allowed_mime_types=LOGO_MIME_TYPES,
        )
        old_stored_file = profile.logo_stored_file
        suffix = Path(filename).suffix
        storage_key = f"company/{profile.company_id}/logo/{uuid4()}{suffix}"
        stored_object = await self.storage_service.upload_bytes(
            key=storage_key,
            content=content,
            filename=filename,
            content_type=mime_type,
        )
        try:
            stored_file = await self.company_repository.upsert_stored_file(
                storage_key=stored_object.key,
                original_filename=filename,
                mime_type=stored_object.mime_type,
                size_bytes=stored_object.size_bytes,
                sha256=stored_object.sha256,
                etag=stored_object.etag,
            )
            updated = await self.company_repository.set_profile_logo_stored_file_id(
                profile, stored_file.id
            )
        except Exception:
            await self.storage_service.delete_object(stored_object.key)
            raise
        if old_stored_file is not None:
            await self.storage_service.delete_object(old_stored_file.storage_key)
            await self.company_repository.delete_stored_file(old_stored_file)
        return await self._profile_result(company_id, updated)

    async def delete_my_profile_logo(self) -> CompanyProfileResult:
        company_user = require_company_profile_user(self.current_user)
        return await self._delete_profile_logo(company_user.company_id)

    async def delete_company_profile_logo(
        self, company_id: UUID
    ) -> CompanyProfileResult:
        require_staff_user(self.current_user)
        await self._ensure_company_exists(company_id, "company_profile_logo")
        return await self._delete_profile_logo(company_id)

    async def _delete_profile_logo(self, company_id: UUID) -> CompanyProfileResult:
        profile = await self.company_repository.get_kp_profile(company_id)
        stored_file = profile.logo_stored_file if profile is not None else None
        if profile is None or stored_file is None:
            return await self._profile_result(company_id, profile)
        updated = await self.company_repository.set_profile_logo_stored_file_id(
            profile, None
        )
        await self.storage_service.delete_object(stored_file.storage_key)
        await self.company_repository.delete_stored_file(stored_file)
        return await self._profile_result(company_id, updated)
