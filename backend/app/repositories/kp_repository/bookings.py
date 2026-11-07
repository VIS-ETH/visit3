from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.core.dates import utc_now
from app.models.company import Company, KpCompanyProfile
from app.models.industry import KpCompanyProfileIndustryLink
from app.models.kp_event import (
    INACTIVE_BOOKING_STATUSES,
    KpBookingCompanyDetails,
    KpBookingCompanyDetailsIndustryLink,
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
)
from app.repositories.base import rel
from app.repositories.kp_repository.inclusions import InclusionsMixin
from app.schemas.kp import BookingServiceInput, CreateBookingInput, UpdateBookingInput

COMPANY_SNAPSHOT_FIELDS = (
    "description",
    "website",
    "brand_name",
    "general_email",
    "general_phone",
    "student_contact_email",
    "places_of_work",
    "employee_count_switzerland",
    "employee_count_worldwide",
    "offers_internships",
    "offers_part_time",
    "offers_theses",
    "offers_graduate_positions",
    "languages",
    "billing_company_name",
    "billing_street",
    "billing_house_number",
    "billing_postal_code",
    "billing_city",
    "billing_country",
    "billing_vat_number",
    "billing_email",
)

ACTIVE_BOOKING = col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES)


class BookingsMixin(InclusionsMixin):
    @staticmethod
    def locked_booking_statement(booking_id: UUID):
        return (
            select(KpEventBooking)
            .where(col(KpEventBooking.id) == booking_id)
            .with_for_update(of=KpEventBooking)
            .execution_options(populate_existing=True)
        )

    async def lock_booking(self, booking_id: UUID) -> Optional[KpEventBooking]:
        await self.session.execute(self.locked_booking_statement(booking_id))
        return await self.get_booking_by_id(booking_id)

    async def list_bookings_for_event(self, event_id: UUID) -> Sequence[KpEventBooking]:
        statement = self._booking_select().where(
            col(KpEventBooking.event_id) == event_id
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_registered_bookings_awaiting_reminder(
        self, today: date
    ) -> Sequence[KpEventBooking]:
        statement = (
            self._booking_select()
            .join(KpEvent, col(KpEvent.id) == col(KpEventBooking.event_id))
            .where(
                col(KpEventBooking.status) == KpBookingStatus.REGISTERED,
                col(KpEventBooking.reminder_sent_at).is_(None),
                col(KpEvent.finalization_deadline) >= today,
            )
            .order_by(col(KpEventBooking.created_at).asc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_bookings_for_company(
        self, company_id: UUID, event_id: UUID | None = None
    ) -> Sequence[KpEventBooking]:
        statement = self._booking_select().where(
            col(KpEventBooking.company_id) == company_id
        )
        if event_id is not None:
            statement = statement.where(col(KpEventBooking.event_id) == event_id)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_pending_offers(self) -> Sequence[KpEventBooking]:
        statement = self._booking_select().where(
            col(KpEventBooking.status) == KpBookingStatus.OFFERED
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_company_active_booking_for_event(
        self, event_id: UUID, company_id: UUID
    ) -> Optional[KpEventBooking]:
        statement = self._booking_select().where(
            col(KpEventBooking.event_id) == event_id,
            col(KpEventBooking.company_id) == company_id,
            ACTIVE_BOOKING,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_company_latest_inactive_booking_for_event(
        self, event_id: UUID, company_id: UUID
    ) -> Optional[KpEventBooking]:
        statement = (
            self._booking_select()
            .where(
                col(KpEventBooking.event_id) == event_id,
                col(KpEventBooking.company_id) == company_id,
                col(KpEventBooking.status).in_(INACTIVE_BOOKING_STATUSES),
            )
            .order_by(col(KpEventBooking.created_at).desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_active_booking_by_booth_number(
        self, event_id: UUID, booth_zone_id: UUID, booth_nr: int
    ) -> Optional[KpEventBooking]:
        statement = select(KpEventBooking).where(
            col(KpEventBooking.event_id) == event_id,
            col(KpEventBooking.booth_zone_id) == booth_zone_id,
            col(KpEventBooking.booth_nr) == booth_nr,
            ACTIVE_BOOKING,
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def count_active_bookings_for_zone(
        self, event_id: UUID, booth_zone_id: UUID
    ) -> int:
        statement = (
            select(func.count())
            .select_from(KpEventBooking)
            .where(
                col(KpEventBooking.event_id) == event_id,
                col(KpEventBooking.booth_zone_id) == booth_zone_id,
                ACTIVE_BOOKING,
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def count_active_bookings_with_service(self, service_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(KpEventBookingService)
            .join(KpEventBooking)
            .where(
                col(KpEventBookingService.service_id) == service_id,
                ACTIVE_BOOKING,
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def count_active_charged_service_quantity(self, service_id: UUID) -> int:
        charged_quantity = case(
            (
                col(KpEventBookingService.quantity)
                > col(KpEventBookingService.included_quantity),
                col(KpEventBookingService.quantity)
                - col(KpEventBookingService.included_quantity),
            ),
            else_=0,
        )
        statement = (
            select(func.coalesce(func.sum(charged_quantity), 0))
            .join(KpEventBooking)
            .where(
                col(KpEventBookingService.service_id) == service_id,
                ACTIVE_BOOKING,
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def get_company(self, company_id: UUID) -> Optional[Company]:
        return await self.session.get(Company, company_id)

    async def get_company_profile(self, company_id: UUID) -> Optional[KpCompanyProfile]:
        statement = (
            select(KpCompanyProfile)
            .where(col(KpCompanyProfile.company_id) == company_id)
            .options(
                selectinload(rel(KpCompanyProfile.kp_contact_user)),
                selectinload(rel(KpCompanyProfile.industry_links)).selectinload(
                    rel(KpCompanyProfileIndustryLink.industry)
                ),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    def _add_company_snapshot(
        self,
        booking_id: UUID,
        company_profile: KpCompanyProfile,
        confirmed_at: datetime,
    ) -> None:
        contact = company_profile.kp_contact_user
        snapshot = self._clone_model(
            KpBookingCompanyDetails,
            company_profile,
            COMPANY_SNAPSHOT_FIELDS,
            booking_id=booking_id,
            confirmed_at=confirmed_at,
            contact_person=contact.display_name if contact else "",
            contact_email=contact.email if contact else None,
            contact_phone=contact.phone_number if contact else None,
        )
        for link in company_profile.industry_links:
            self.session.add(
                KpBookingCompanyDetailsIndustryLink(
                    booking_company_details_id=snapshot.id,
                    industry_id=link.industry_id,
                    industry_name=link.industry.name,
                )
            )

    async def create_booking(
        self,
        event_id: UUID,
        company_id: UUID,
        booth_zone_id: UUID,
        create_booking_input: CreateBookingInput,
        services: Sequence[BookingServiceInput] = (),
        included_quantities: Mapping[UUID, int] | None = None,
        company_profile: Optional[KpCompanyProfile] = None,
        confirmed_at: Optional[datetime] = None,
    ) -> KpEventBooking:
        async with self.committing():
            booking = KpEventBooking(
                **create_booking_input.model_dump(),
                event_id=event_id,
                company_id=company_id,
                booth_zone_id=booth_zone_id,
            )
            self._validate_model(booking)
            self.session.add(booking)
            await self.session.flush()

            if company_profile is not None:
                self._add_company_snapshot(
                    booking.id,
                    company_profile,
                    confirmed_at or utc_now(),
                )

            for item in services:
                booking_service = KpEventBookingService(
                    booking_id=booking.id,
                    service_id=item.service_id,
                    quantity=item.quantity,
                    included_quantity=0,
                )
                self._validate_model(booking_service)
                self.session.add(booking_service)
            await self.session.flush()
            await self._sync_inclusions(booking.id, included_quantities or {})
        return await self.get_booking_by_id(booking.id) or booking

    async def accept_offer(
        self,
        booking: KpEventBooking,
        company_profile: KpCompanyProfile,
        accepted_at: datetime,
    ) -> KpEventBooking:
        async with self.committing():
            snapshot_ids = select(col(KpBookingCompanyDetails.id)).where(
                col(KpBookingCompanyDetails.booking_id) == booking.id
            )
            await self.hard_delete_where(
                KpBookingCompanyDetailsIndustryLink,
                col(KpBookingCompanyDetailsIndustryLink.booking_company_details_id).in_(
                    snapshot_ids
                ),
            )
            await self.hard_delete_where(
                KpBookingCompanyDetails,
                col(KpBookingCompanyDetails.booking_id) == booking.id,
            )
            booking.status = KpBookingStatus.REGISTERED
            booking.status_changed_at = accepted_at
            self.session.add(booking)
            self._add_company_snapshot(booking.id, company_profile, accepted_at)
        return await self.get_booking_by_id(booking.id) or booking

    async def update_booking(
        self, booking: KpEventBooking, update_booking_input: UpdateBookingInput
    ) -> KpEventBooking:
        async with self.committing():
            booking.sqlmodel_update(update_booking_input.model_dump(exclude_unset=True))
            self._validate_model(booking)
            self.session.add(booking)
        return await self.get_booking_by_id(booking.id) or booking

    async def move_booking_to_zone(
        self,
        booking: KpEventBooking,
        zone: KpEventBoothZone,
        *,
        clear_whole_waitlist: bool,
    ) -> KpEventBooking:
        async with self.committing():
            booking.booth_zone_id = zone.id
            booking.booth_nr = None
            self._validate_model(booking)
            self.session.add(booking)

            conditions = [col(KpEventBookingUpgradeWaitlist.booking_id) == booking.id]
            if not clear_whole_waitlist:
                conditions.append(
                    col(KpEventBookingUpgradeWaitlist.target_booth_zone_id) == zone.id
                )
            await self.hard_delete_where(KpEventBookingUpgradeWaitlist, *conditions)
            await self.session.flush()
            await self._sync_inclusions(
                booking.id,
                {
                    included_service.service_id: included_service.included_quantity
                    for included_service in zone.included_services
                },
            )
        return await self.get_booking_by_id(booking.id) or booking

    async def delete_booking(self, booking: KpEventBooking) -> None:
        async with self.committing():
            for entry in booking.upgrade_waitlist_entries:
                self.delete(entry)
            self.delete(booking)
