from collections.abc import Sequence
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.selectable import Select
from sqlmodel import col, select

from app.core.utils import normalize_email
from app.models.company import Company, CompanyInvite, KpCompanyProfile
from app.models.industry import Industry, KpCompanyProfileIndustryLink
from app.models.kp_event import (
    INACTIVE_BOOKING_STATUSES,
    KpBookingCompanyDetails,
    KpBookingCompanyDetailsIndustryLink,
    KpEvent,
    KpEventBooking,
    KpEventBookingUpgradeWaitlist,
    KpEventRegistrationException,
    NameTag,
)
from app.models.storage import StoredFile
from app.models.user import User
from app.repositories.base import BaseRepository, rel
from app.schemas.company import UpdateCompanyProfileInput


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: AsyncSession):
        super().__init__(Company, session)

    async def create_company(self, name: str) -> Company:
        try:
            company = Company(name=name)
            self.session.add(company)
            await self.session.commit()
            await self.session.refresh(company)
            return company
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_by_name(self, name: str) -> Optional[Company]:
        return await self._get_by_field(col(Company.name), name)

    async def get_users(self, company: Company) -> Sequence[User]:
        statement = (
            select(User)
            .where(col(User.company_id) == company.id)
            .options(selectinload(rel(User.company)))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_company_user_by_id(self, user_id: UUID) -> Optional[User]:
        statement = (
            select(User)
            .where(col(User.id) == user_id)
            .options(selectinload(rel(User.company)))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_companies(self) -> Sequence[Company]:
        statement = select(Company)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def count_users(self, company_id: UUID) -> int:
        statement = select(func.count(col(User.id))).where(
            col(User.company_id) == company_id, self._not_deleted(User)
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    def _matching_companies(self, query: str | None) -> Select[tuple[Company]]:
        term = (query or "").strip()
        conditions = (
            [col(Company.name).icontains(term, autoescape=True)] if term else []
        )
        return select(Company).where(self._not_deleted(Company), *conditions)

    async def count_companies(self, query: str | None) -> int:
        statement = self._matching_companies(query).with_only_columns(
            func.count(col(Company.id))
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def get_company_overviews(
        self,
        query: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Sequence[tuple[UUID, str, int, int]]:
        users_count = (
            select(func.count(col(User.id)))
            .where(col(User.company_id) == col(Company.id), self._not_deleted(User))
            .correlate(Company)
            .scalar_subquery()
        )
        bookings_count = (
            select(func.count(col(KpEventBooking.id)))
            .where(
                col(KpEventBooking.company_id) == col(Company.id),
                col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES),
                self._not_deleted(KpEventBooking),
            )
            .correlate(Company)
            .scalar_subquery()
        )
        statement = (
            self._matching_companies(query)
            .with_only_columns(
                col(Company.id), col(Company.name), users_count, bookings_count
            )
            .order_by(col(Company.name))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            (company_id, name, users, bookings)
            for company_id, name, users, bookings in result.all()
        ]

    async def get_user_by_email(self, email: str) -> Optional[User]:
        statement = select(User).where(col(User.email) == normalize_email(email))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_company_with_users(self, company_id: UUID) -> Optional[Company]:
        statement = (
            select(Company)
            .where(col(Company.id) == company_id)
            .options(selectinload(rel(Company.users)))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_kp_profile(self, company_id: UUID) -> Optional[KpCompanyProfile]:
        statement = (
            select(KpCompanyProfile)
            .where(col(KpCompanyProfile.company_id) == company_id)
            .options(
                selectinload(rel(KpCompanyProfile.kp_contact_user)),
                selectinload(rel(KpCompanyProfile.logo_stored_file)),
                selectinload(rel(KpCompanyProfile.industry_links)).selectinload(
                    rel(KpCompanyProfileIndustryLink.industry)
                ),
            )
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_industries_by_ids(
        self, industry_ids: list[UUID]
    ) -> Sequence[Industry]:
        statement = select(Industry).where(col(Industry.id).in_(industry_ids))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def upsert_kp_profile(
        self, company_id: UUID, profile_input: UpdateCompanyProfileInput
    ) -> KpCompanyProfile:
        try:
            profile = await self.get_kp_profile(company_id)
            if profile is None:
                profile = KpCompanyProfile(company_id=company_id)

            profile.sqlmodel_update(profile_input.model_dump(exclude={"industry_ids"}))
            self._validate_model(
                profile,
                exclude={
                    "company",
                    "kp_contact_user",
                    "logo_stored_file",
                    "industry_links",
                },
            )
            if profile.is_complete and profile.profile_completed_at is None:
                profile.profile_completed_at = datetime.now(timezone.utc)
            self.session.add(profile)
            await self.session.flush()
            await self._replace_profile_industries(profile, profile_input.industry_ids)
            await self.session.commit()
            return await self.get_kp_profile(company_id) or profile
        except Exception as e:
            await self.session.rollback()
            raise e

    async def _replace_profile_industries(
        self, profile: KpCompanyProfile, industry_ids: list[UUID]
    ) -> None:
        await self.hard_delete_where(
            KpCompanyProfileIndustryLink,
            col(KpCompanyProfileIndustryLink.profile_id) == profile.id,
        )
        for industry_id in dict.fromkeys(industry_ids):
            self.session.add(
                KpCompanyProfileIndustryLink(
                    profile_id=profile.id, industry_id=industry_id
                )
            )

    async def set_profile_logo_stored_file_id(
        self, profile: KpCompanyProfile, stored_file_id: UUID | None
    ) -> KpCompanyProfile:
        try:
            profile.logo_stored_file_id = stored_file_id
            self.session.add(profile)
            await self.session.commit()
            return await self.get_kp_profile(profile.company_id) or profile
        except Exception as e:
            await self.session.rollback()
            raise e

    async def upsert_stored_file(
        self,
        storage_key: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        etag: str | None,
    ) -> StoredFile:
        try:
            stored_file = StoredFile(
                storage_key=storage_key,
                original_filename=original_filename,
                mime_type=mime_type,
                size_bytes=size_bytes,
                sha256=sha256,
                etag=etag,
            )
            self._validate_model(stored_file)
            self.session.add(stored_file)
            await self.session.commit()
            await self.session.refresh(stored_file)
            return stored_file
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_stored_file(self, stored_file: StoredFile) -> None:
        try:
            await self.session.delete(stored_file)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_company_with_users(self, company: Company):
        try:
            await self._delete_company_owned_rows(company.id)
            await self.delete_where(
                User,
                col(User.company_id) == company.id,
            )
            self.delete(company)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_company_keep_users(self, company: Company):
        try:
            await self._delete_company_owned_rows(company.id)
            await self.update_where(
                User, col(User.company_id) == company.id, company_id=None
            )
            self.delete(company)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def has_bookings_for_upcoming_events(self, company_id: UUID) -> bool:
        statement = (
            select(KpEventBooking)
            .join(KpEvent, col(KpEvent.id) == col(KpEventBooking.event_id))
            .where(
                col(KpEventBooking.company_id) == company_id,
                col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES),
                col(KpEvent.event_date) >= date.today(),
            )
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalars().first() is not None

    async def is_last_member_of_booked_company(self, company_id: UUID) -> bool:
        if await self.count_users(company_id) > 1:
            return False
        return await self.has_bookings_for_upcoming_events(company_id)

    async def _delete_company_owned_rows(self, company_id: UUID) -> None:
        profile_ids = (
            select(col(KpCompanyProfile.id))
            .where(col(KpCompanyProfile.company_id) == company_id)
            .scalar_subquery()
        )
        await self.delete_where(
            KpCompanyProfileIndustryLink,
            col(KpCompanyProfileIndustryLink.profile_id).in_(profile_ids),
        )
        await self.delete_where(
            KpCompanyProfile,
            col(KpCompanyProfile.company_id) == company_id,
        )
        await self.delete_where(
            CompanyInvite,
            col(CompanyInvite.company_id) == company_id,
        )
        await self.delete_where(
            KpEventRegistrationException,
            col(KpEventRegistrationException.company_id) == company_id,
        )

        booking_ids = (
            select(col(KpEventBooking.id))
            .where(col(KpEventBooking.company_id) == company_id)
            .scalar_subquery()
        )
        await self.delete_where(
            NameTag,
            col(NameTag.booking_id).in_(booking_ids),
        )
        await self.delete_where(
            KpEventBookingUpgradeWaitlist,
            col(KpEventBookingUpgradeWaitlist.booking_id).in_(booking_ids),
        )
        snapshot_ids = (
            select(col(KpBookingCompanyDetails.id))
            .where(col(KpBookingCompanyDetails.booking_id).in_(booking_ids))
            .scalar_subquery()
        )
        await self.delete_where(
            KpBookingCompanyDetailsIndustryLink,
            col(KpBookingCompanyDetailsIndustryLink.booking_company_details_id).in_(
                snapshot_ids
            ),
        )
        await self.delete_where(
            KpBookingCompanyDetails,
            col(KpBookingCompanyDetails.booking_id).in_(booking_ids),
        )
        await self.delete_where(
            KpEventBooking,
            col(KpEventBooking.company_id) == company_id,
        )

    async def update_company_name(self, company: Company, name: str) -> Company:
        try:
            company.name = name
            self.session.add(company)
            await self.session.commit()
            await self.session.refresh(company)
            return company
        except Exception as e:
            await self.session.rollback()
            raise e

    async def _load_user_company(self, user: User) -> User:
        statement = (
            select(User)
            .where(col(User.id) == user.id)
            .options(selectinload(rel(User.company)))
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() or user

    async def assign_user(self, user: User, company_id: UUID) -> User:
        try:
            user.company_id = company_id
            self.session.add(user)
            await self.session.commit()
            return await self._load_user_company(user)
        except Exception as e:
            await self.session.rollback()
            raise e

    async def remove_user_from_company(self, user: User, company: Company) -> User:
        try:
            profile = await self.get_kp_profile(company.id)
            if profile is not None and profile.kp_contact_user_id == user.id:
                profile.kp_contact_user_id = None
                self.session.add(profile)

            user.company_id = None
            self.session.add(user)
            await self.session.commit()
            return await self._load_user_company(user)
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_invite(
        self,
        token: str,
        company_id: UUID,
        invited_email: str,
        expires_at: datetime,
    ) -> CompanyInvite:
        try:
            invite = CompanyInvite(
                token=token,
                company_id=company_id,
                invited_email=invited_email,
                expires_at=expires_at,
            )
            self._validate_model(invite, exclude={"company"})
            self.session.add(invite)
            await self.session.commit()
            await self.session.refresh(invite)
            return invite
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_pending_invite(
        self, company_id: UUID, invited_email: str
    ) -> Optional[CompanyInvite]:
        statement = select(CompanyInvite).where(
            col(CompanyInvite.company_id) == company_id,
            col(CompanyInvite.invited_email) == invited_email,
            col(CompanyInvite.is_used) == False,
            col(CompanyInvite.expires_at) > datetime.now(timezone.utc),
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_invite_by_token(self, token: str) -> Optional[CompanyInvite]:
        statement = select(CompanyInvite).where(col(CompanyInvite.token) == token)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_invite_used(self, invite: CompanyInvite):
        try:
            invite.is_used = True
            self.session.add(invite)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def cleanup_expired_invites(self) -> None:
        try:
            now = datetime.now(timezone.utc)
            await self.hard_delete_where(
                CompanyInvite,
                (col(CompanyInvite.expires_at) < now)
                | (col(CompanyInvite.is_used) == True),
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
