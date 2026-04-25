from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpBookingCompanyDetailsIndustryLink,
    KpCompanyLanguage,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBoothZone,
    KpEventRegistrationException,
    KpEventService,
    KpIndustry,
    NameTag,
)
from app.repositories.base import BaseRepository


class KpRepository(BaseRepository[KpEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(KpEvent, session)

    def _validate_booking(self, booking: KpEventBooking) -> KpEventBooking:
        return self._validate_model(
            booking,
            exclude={
                "event",
                "company",
                "booth_zone",
                "main_contact",
                "services",
                "name_tags",
                "company_details",
            },
        )

    def _booking_select(self):
        return select(KpEventBooking).options(
            selectinload(KpEventBooking.event),
            selectinload(KpEventBooking.company),
            selectinload(KpEventBooking.booth_zone),
            selectinload(KpEventBooking.main_contact),
            selectinload(KpEventBooking.services).selectinload(
                KpEventBookingService.service
            ),
            selectinload(KpEventBooking.name_tags),
            selectinload(KpEventBooking.company_details)
            .selectinload(KpBookingCompanyDetails.industry_links)
            .selectinload(KpBookingCompanyDetailsIndustryLink.industry),
        )

    async def get_by_name(self, name: str) -> Optional[KpEvent]:
        return await self._get_by_field(KpEvent.name, name)

    async def list_kps(self) -> list[KpEvent]:
        statement = select(KpEvent).order_by(KpEvent.event_date.desc())
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_latest_kp(self) -> Optional[KpEvent]:
        statement = select(KpEvent).order_by(KpEvent.event_date.desc()).limit(1)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_kp(
        self,
        name: str,
        registration_open: date,
        registration_end: date,
        finalization_deadline: date,
        nametags_deadline: date,
        event_date: date,
    ) -> KpEvent:
        try:
            event = KpEvent(
                name=name,
                registration_open=registration_open,
                registration_end=registration_end,
                finalization_deadline=finalization_deadline,
                nametags_deadline=nametags_deadline,
                event_date=event_date,
            )
            self._validate_model(event, exclude={"booth_zones", "bookings", "services"})
            self.session.add(event)
            await self.session.commit()
            await self.session.refresh(event)
            return event
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_booking_by_id(self, booking_id: UUID) -> Optional[KpEventBooking]:
        statement = self._booking_select().where(KpEventBooking.id == booking_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_bookings_for_event(self, event_id: UUID) -> list[KpEventBooking]:
        statement = self._booking_select().where(KpEventBooking.event_id == event_id)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_bookings_for_company(
        self, company_id: UUID, event_id: UUID | None = None
    ) -> list[KpEventBooking]:
        statement = self._booking_select().where(
            KpEventBooking.company_id == company_id
        )
        if event_id is not None:
            statement = statement.where(KpEventBooking.event_id == event_id)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def create_booking(
        self,
        event_id: UUID,
        company_id: UUID,
        booth_zone_id: UUID,
        main_contact_id: UUID,
        booth_nr: int,
        finalized: bool = False,
    ) -> KpEventBooking:
        try:
            booking = KpEventBooking(
                event_id=event_id,
                company_id=company_id,
                booth_zone_id=booth_zone_id,
                main_contact_id=main_contact_id,
                booth_nr=booth_nr,
                finalized=finalized,
            )
            self._validate_booking(booking)
            self.session.add(booking)
            await self.session.commit()
            return await self.get_booking_by_id(booking.id) or booking
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_booking(
        self,
        booking: KpEventBooking,
        booth_zone_id: UUID | None = None,
        main_contact_id: UUID | None = None,
        booth_nr: int | None = None,
        finalized: bool | None = None,
    ) -> KpEventBooking:
        try:
            if booth_zone_id is not None:
                booking.booth_zone_id = booth_zone_id
            if main_contact_id is not None:
                booking.main_contact_id = main_contact_id
            if booth_nr is not None:
                booking.booth_nr = booth_nr
            if finalized is not None:
                booking.finalized = finalized

            self._validate_booking(booking)
            self.session.add(booking)
            await self.session.commit()
            return await self.get_booking_by_id(booking.id) or booking
        except Exception as e:
            await self.session.rollback()
            raise e

    async def list_booth_zones(self, event_id: UUID) -> list[KpEventBoothZone]:
        statement = (
            select(KpEventBoothZone)
            .where(KpEventBoothZone.event_id == event_id)
            .order_by(KpEventBoothZone.order.asc(), KpEventBoothZone.name.asc())
            .options(selectinload(KpEventBoothZone.included_services))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_booth_zone_by_id(
        self, booth_zone_id: UUID
    ) -> Optional[KpEventBoothZone]:
        statement = (
            select(KpEventBoothZone)
            .where(KpEventBoothZone.id == booth_zone_id)
            .options(selectinload(KpEventBoothZone.included_services))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_booth_zone_by_name(
        self, event_id: UUID, name: str
    ) -> Optional[KpEventBoothZone]:
        statement = (
            select(KpEventBoothZone)
            .where(KpEventBoothZone.event_id == event_id, KpEventBoothZone.name == name)
            .options(selectinload(KpEventBoothZone.included_services))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_services(self, event_id: UUID) -> list[KpEventService]:
        statement = (
            select(KpEventService)
            .where(KpEventService.event_id == event_id)
            .order_by(KpEventService.order.asc(), KpEventService.name.asc())
            .options(selectinload(KpEventService.requirements))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_service_by_id(self, service_id: UUID) -> Optional[KpEventService]:
        statement = (
            select(KpEventService)
            .where(KpEventService.id == service_id)
            .options(selectinload(KpEventService.requirements))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_service_by_name(
        self, event_id: UUID, name: str
    ) -> Optional[KpEventService]:
        statement = (
            select(KpEventService)
            .where(KpEventService.event_id == event_id, KpEventService.name == name)
            .options(selectinload(KpEventService.requirements))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_industries(self) -> list[KpIndustry]:
        statement = select(KpIndustry).order_by(KpIndustry.name.asc())
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_industry_by_id(self, industry_id: UUID) -> Optional[KpIndustry]:
        return await self._get_by_field(KpIndustry.id, industry_id)

    async def get_industry_by_name(self, name: str) -> Optional[KpIndustry]:
        return await self._get_by_field(KpIndustry.name, name)

    async def create_industry(self, name: str) -> KpIndustry:
        try:
            industry = KpIndustry(name=name)
            self.session.add(industry)
            await self.session.commit()
            await self.session.refresh(industry)
            return industry
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_name_tag(
        self, booking_id: UUID, first_name: str, last_name: str, position: str
    ) -> NameTag:
        try:
            name_tag = NameTag(
                booking_id=booking_id,
                first_name=first_name,
                last_name=last_name,
                position=position,
            )
            self._validate_model(name_tag, exclude={"booking"})
            self.session.add(name_tag)
            await self.session.commit()
            await self.session.refresh(name_tag)
            return name_tag
        except Exception as e:
            await self.session.rollback()
            raise e

    async def list_registration_exceptions(
        self, event_id: UUID
    ) -> list[KpEventRegistrationException]:
        statement = select(KpEventRegistrationException).where(
            KpEventRegistrationException.event_id == event_id
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_registration_exception(
        self, event_id: UUID, company_id: UUID
    ) -> Optional[KpEventRegistrationException]:
        statement = select(KpEventRegistrationException).where(
            KpEventRegistrationException.event_id == event_id,
            KpEventRegistrationException.company_id == company_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_registration_exception(
        self, event_id: UUID, company_id: UUID, allowed_until: date
    ) -> KpEventRegistrationException:
        try:
            exception = await self.get_registration_exception(event_id, company_id)
            if exception is None:
                exception = KpEventRegistrationException(
                    event_id=event_id,
                    company_id=company_id,
                    allowed_until=allowed_until,
                )
            else:
                exception.allowed_until = allowed_until
            self.session.add(exception)
            await self.session.commit()
            await self.session.refresh(exception)
            return exception
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_registration_exception(
        self, exception: KpEventRegistrationException
    ) -> None:
        try:
            await self.session.delete(exception)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def upsert_company_details(
        self,
        booking_id: UUID,
        profile: str | None = None,
        brand_name: str | None = None,
        address: str | None = None,
        contact_person: str | None = None,
        places_of_work: str | None = None,
        employees_count: int | None = None,
        employees_count_switzerland: int | None = None,
        offer_internship: bool | None = None,
        offer_part_time: bool | None = None,
        offer_thesis: bool | None = None,
        languages: list[KpCompanyLanguage] | None = None,
    ) -> KpBookingCompanyDetails:
        try:
            statement = select(KpBookingCompanyDetails).where(
                KpBookingCompanyDetails.booking_id == booking_id
            )
            result = await self.session.execute(statement)
            company_details = result.scalar_one_or_none()

            if company_details is None:
                company_details = KpBookingCompanyDetails(booking_id=booking_id)

            if profile is not None:
                company_details.profile = profile
            if brand_name is not None:
                company_details.brand_name = brand_name
            if address is not None:
                company_details.address = address
            if contact_person is not None:
                company_details.contact_person = contact_person
            if places_of_work is not None:
                company_details.places_of_work = places_of_work
            if employees_count is not None:
                company_details.employees_count = employees_count
            if employees_count_switzerland is not None:
                company_details.employees_count_switzerland = (
                    employees_count_switzerland
                )
            if offer_internship is not None:
                company_details.offer_internship = offer_internship
            if offer_part_time is not None:
                company_details.offer_part_time = offer_part_time
            if offer_thesis is not None:
                company_details.offer_thesis = offer_thesis
            if languages is not None:
                company_details.languages = languages

            self.session.add(company_details)
            await self.session.commit()
            await self.session.refresh(company_details)
            return company_details
        except Exception as e:
            await self.session.rollback()
            raise e
