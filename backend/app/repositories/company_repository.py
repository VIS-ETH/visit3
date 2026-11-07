from collections.abc import Sequence
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.selectable import Select
from sqlmodel import col, select

from app.core.dates import local_today, utc_now
from app.core.exceptions import CompanyNameTaken, UserAlreadyInCompany
from app.core.utils import hash_str, normalize_email
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
from app.models.user import User
from app.repositories.base import BaseRepository, ordered, rel
from app.repositories.change_repository import company_changed_since
from app.repositories.stored_file_queries import StoredFileQueries
from app.schemas.company import (
    CompanyFilter,
    CompanySort,
    UpdateCompanyProfileInput,
)
from app.schemas.sorting import SortDirection


class CompanyRepository(BaseRepository[Company], StoredFileQueries):
    def __init__(self, session: AsyncSession):
        super().__init__(Company, session)

    async def create_company(self, name: str) -> Company:
        try:
            async with self.committing():
                company = Company(name=name)
                self.session.add(company)
        except IntegrityError:
            raise CompanyNameTaken(f"create_company:{name}") from None
        await self.session.refresh(company)
        return company

    async def create_company_with_founder(self, name: str, founder_id: UUID) -> Company:
        try:
            async with self.committing():
                founder = await self.lock_model_by_id(User, founder_id)
                if founder is None or founder.company_id is not None:
                    raise UserAlreadyInCompany(f"create_company:{founder_id}")
                company = Company(name=name)
                self.session.add(company)
                await self.session.flush()
                founder.company_id = company.id
                self.session.add(founder)
        except IntegrityError:
            raise CompanyNameTaken(f"create_company:{name}") from None
        await self.session.refresh(company)
        return company

    async def get_by_name(self, name: str) -> Optional[Company]:
        statement = select(Company).where(
            self._not_deleted(Company),
            func.lower(col(Company.name)) == name.lower(),
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

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

    async def count_users(self, company_id: UUID) -> int:
        statement = select(func.count(col(User.id))).where(
            col(User.company_id) == company_id, self._not_deleted(User)
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    def _matching_companies(
        self,
        query: str | None,
        company_filter: CompanyFilter = CompanyFilter.ALL,
        changed_since: datetime | None = None,
        company_id: UUID | None = None,
    ) -> Select[tuple[Company]]:
        term = (query or "").strip()
        conditions = (
            [col(Company.name).icontains(term, autoescape=True)] if term else []
        )
        if company_filter is CompanyFilter.UNCONFIRMED:
            conditions.append(col(Company.confirmed_at).is_(None))
        if company_filter is CompanyFilter.NEW and changed_since is not None:
            conditions.append(company_changed_since(changed_since))
        if company_id is not None:
            conditions.append(col(Company.id) == company_id)
        return select(Company).where(self._not_deleted(Company), *conditions)

    async def count_companies(
        self,
        query: str | None,
        company_filter: CompanyFilter = CompanyFilter.ALL,
        changed_since: datetime | None = None,
        company_id: UUID | None = None,
    ) -> int:
        statement = self._matching_companies(
            query, company_filter, changed_since, company_id
        ).with_only_columns(func.count(col(Company.id)))
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def get_company_overviews(
        self,
        query: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
        sort: CompanySort = CompanySort.NAME,
        direction: SortDirection = SortDirection.ASC,
        company_filter: CompanyFilter = CompanyFilter.ALL,
        changed_since: datetime | None = None,
        company_id: UUID | None = None,
        unconfirmed_first: bool = False,
    ) -> Sequence[tuple[UUID, str, datetime | None, int, int, int]]:
        users_count = (
            select(func.count(col(User.id)))
            .where(col(User.company_id) == col(Company.id), self._not_deleted(User))
            .correlate(Company)
            .scalar_subquery()
        )
        new_members_count = (
            select(func.count(col(User.id)))
            .where(
                col(User.company_id) == col(Company.id),
                col(User.new_in_company_since).is_not(None),
                self._not_deleted(User),
            )
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
        sort_key = {
            CompanySort.NAME: func.lower(col(Company.name)),
            CompanySort.MEMBERS: users_count,
            CompanySort.BOOKINGS: bookings_count,
        }[sort]
        pinned = [col(Company.confirmed_at).is_not(None)] if unconfirmed_first else []
        statement = (
            self._matching_companies(query, company_filter, changed_since, company_id)
            .with_only_columns(
                col(Company.id),
                col(Company.name),
                col(Company.confirmed_at),
                users_count,
                bookings_count,
                new_members_count,
            )
            .order_by(
                *pinned,
                *ordered([sort_key], direction),
                func.lower(col(Company.name)),
                col(Company.id),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            (company_id, name, confirmed_at, users, bookings, new_members)
            for company_id, name, confirmed_at, users, bookings, new_members in (
                result.all()
            )
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
        async with self.committing():
            profile = await self.get_kp_profile(company_id)
            if profile is None:
                profile = KpCompanyProfile(company_id=company_id)

            profile.sqlmodel_update(profile_input.model_dump(exclude={"industry_ids"}))
            self._validate_model(profile)
            if profile.is_complete and profile.profile_completed_at is None:
                profile.profile_completed_at = utc_now()
            self.session.add(profile)
            await self.session.flush()
            await self._replace_profile_industries(profile, profile_input.industry_ids)
            await self._fill_blank_snapshot_fields(profile)
        return await self.get_kp_profile(company_id) or profile

    async def _fill_blank_snapshot_fields(self, profile: KpCompanyProfile) -> None:
        active_booking_ids = select(col(KpEventBooking.id)).where(
            col(KpEventBooking.company_id) == profile.company_id,
            col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES),
            self._not_deleted(KpEventBooking),
        )
        if profile.description.strip():
            await self.update_where(
                KpBookingCompanyDetails,
                col(KpBookingCompanyDetails.booking_id).in_(active_booking_ids),
                func.trim(col(KpBookingCompanyDetails.description)) == "",
                description=profile.description,
            )
        if profile.general_email:
            await self.update_where(
                KpBookingCompanyDetails,
                col(KpBookingCompanyDetails.booking_id).in_(active_booking_ids),
                func.coalesce(func.trim(col(KpBookingCompanyDetails.general_email)), "")
                == "",
                general_email=profile.general_email,
            )
        if profile.student_contact_email:
            await self.update_where(
                KpBookingCompanyDetails,
                col(KpBookingCompanyDetails.booking_id).in_(active_booking_ids),
                func.coalesce(
                    func.trim(col(KpBookingCompanyDetails.student_contact_email)), ""
                )
                == "",
                student_contact_email=profile.student_contact_email,
            )

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
        async with self.committing():
            profile.logo_stored_file_id = stored_file_id
            self.session.add(profile)
        return await self.get_kp_profile(profile.company_id) or profile

    async def delete_company_with_users(self, company: Company):
        async with self.committing():
            await self._delete_company_owned_rows(company.id)
            await self.delete_where(
                User,
                col(User.company_id) == company.id,
            )
            self.delete(company)

    async def delete_company_keep_users(self, company: Company):
        async with self.committing():
            await self._delete_company_owned_rows(company.id)
            await self.update_where(
                User,
                col(User.company_id) == company.id,
                company_id=None,
                new_in_company_since=None,
            )
            self.delete(company)

    async def has_bookings_for_upcoming_events(self, company_id: UUID) -> bool:
        statement = (
            select(KpEventBooking)
            .join(KpEvent, col(KpEvent.id) == col(KpEventBooking.event_id))
            .where(
                col(KpEventBooking.company_id) == company_id,
                col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES),
                col(KpEvent.event_date) >= local_today(),
            )
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalars().first() is not None

    async def is_last_member_of_booked_company(self, company_id: UUID) -> bool:
        await self.lock_model_by_id(Company, company_id)
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

    async def update_company_name(
        self, company: Company, name: str, *, unconfirm: bool = False
    ) -> Company:
        async with self.committing():
            company.name = name
            if unconfirm:
                company.confirmed_at = None
            self.session.add(company)
        await self.session.refresh(company)
        return company

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
        async with self.committing():
            user.company_id = company_id
            user.new_in_company_since = utc_now()
            self.session.add(user)
        return await self._load_user_company(user)

    async def confirm_company(self, company: Company) -> Company:
        async with self.committing():
            company.confirmed_at = utc_now()
            self.session.add(company)
        await self.session.refresh(company)
        return company

    async def acknowledge_new_members(self, company: Company) -> None:
        async with self.committing():
            await self.update_where(
                User,
                col(User.company_id) == company.id,
                new_in_company_since=None,
            )

    async def remove_user_from_company(self, user: User, company: Company) -> User:
        async with self.committing():
            profile = await self.get_kp_profile(company.id)
            if profile is not None and profile.kp_contact_user_id == user.id:
                profile.kp_contact_user_id = None
                self.session.add(profile)

            user.company_id = None
            user.new_in_company_since = None
            self.session.add(user)
        return await self._load_user_company(user)

    async def create_invite(
        self,
        token: str,
        company_id: UUID,
        invited_email: str,
        expires_at: datetime,
        invited_by_user_id: UUID | None = None,
    ) -> CompanyInvite:
        async with self.committing():
            invite = CompanyInvite(
                token=hash_str(token),
                company_id=company_id,
                invited_email=invited_email,
                expires_at=expires_at,
                invited_by_user_id=invited_by_user_id,
            )
            self._validate_model(invite)
            self.session.add(invite)
        await self.session.refresh(invite)
        return invite

    async def get_pending_invite(
        self, company_id: UUID, invited_email: str
    ) -> Optional[CompanyInvite]:
        statement = select(CompanyInvite).where(
            col(CompanyInvite.company_id) == company_id,
            col(CompanyInvite.invited_email) == invited_email,
            col(CompanyInvite.is_used) == False,
            col(CompanyInvite.expires_at) > utc_now(),
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_invite_by_token(self, token: str) -> Optional[CompanyInvite]:
        statement = select(CompanyInvite).where(
            col(CompanyInvite.token) == hash_str(token)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke_open_invites_by(self, user_id: UUID) -> None:
        async with self.committing():
            await self.hard_delete_where(
                CompanyInvite,
                col(CompanyInvite.invited_by_user_id) == user_id,
                col(CompanyInvite.is_used) == False,
            )

    async def delete_invite(self, invite: CompanyInvite) -> None:
        async with self.committing():
            await self.hard_delete(invite)

    async def mark_invite_used(self, invite: CompanyInvite):
        async with self.committing():
            invite.is_used = True
            self.session.add(invite)

    async def cleanup_expired_invites(self) -> None:
        async with self.committing():
            now = utc_now()
            await self.hard_delete_where(
                CompanyInvite,
                (col(CompanyInvite.expires_at) < now)
                | (col(CompanyInvite.is_used) == True),
            )
