from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpBookingCompanyDetailsIndustryLink,
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventRegistrationException,
    KpEventService,
    KpEventServiceRequirement,
    KpIndustry,
    NameTag,
)
from app.models.storage import StoredFile
from app.repositories.base import BaseRepository
from app.schemas.kp import (
    CreateBookingInput,
    CreateBoothZoneInput,
    CreateIndustryInput,
    CreateKpInput,
    CreateServiceInput,
    UpdateBookingInput,
    UpdateBoothZoneInput,
    UpdateKpInput,
    UpdateServiceInput,
    UpsertCompanyDetailsInput,
)


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
            selectinload(KpEventBooking.services).selectinload(
                KpEventBookingService.service
            ),
            selectinload(KpEventBooking.name_tags),
            selectinload(KpEventBooking.upgrade_waitlist_entries).selectinload(
                KpEventBookingUpgradeWaitlist.target_booth_zone
            ),
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

    async def create_kp(self, create_kp_input: CreateKpInput) -> KpEvent:
        try:
            event = KpEvent(**create_kp_input.model_dump())
            self._validate_model(event, exclude={"booth_zones", "bookings", "services"})
            self.session.add(event)
            await self.session.commit()
            await self.session.refresh(event)
            return event
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_kp(
        self, event: KpEvent, update_kp_input: UpdateKpInput
    ) -> KpEvent:
        try:
            event.sqlmodel_update(update_kp_input.model_dump(exclude_unset=True))
            self._validate_model(
                event,
                exclude={
                    "booth_zones",
                    "bookings",
                    "services",
                    "registration_exceptions",
                },
            )
            self.session.add(event)
            await self.session.commit()
            await self.session.refresh(event)
            return event
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_booth_zone(
        self, event_id: UUID, create_booth_zone_input: CreateBoothZoneInput
    ) -> KpEventBoothZone:
        try:
            zone = KpEventBoothZone(
                **create_booth_zone_input.model_dump(),
                event_id=event_id,
            )
            self._validate_model(
                zone,
                exclude={
                    "event",
                    "included_services",
                    "bookings",
                    "upgrade_waitlist_entries",
                },
            )
            self.session.add(zone)
            await self.session.commit()
            await self.session.refresh(zone)
            return zone
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_booth_zone(
        self, zone: KpEventBoothZone, update_booth_zone_input: UpdateBoothZoneInput
    ) -> KpEventBoothZone:
        try:
            zone.sqlmodel_update(update_booth_zone_input.model_dump(exclude_unset=True))
            self._validate_model(
                zone,
                exclude={
                    "event",
                    "included_services",
                    "bookings",
                    "upgrade_waitlist_entries",
                },
            )
            self.session.add(zone)
            await self.session.commit()
            await self.session.refresh(zone)
            return zone
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_booth_zone(self, zone: KpEventBoothZone) -> None:
        try:
            await self.session.delete(zone)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_service(
        self, event_id: UUID, create_service_input: CreateServiceInput
    ) -> KpEventService:
        try:
            service = KpEventService(
                **create_service_input.model_dump(),
                event_id=event_id,
            )
            self._validate_model(
                service,
                exclude={"event", "booth_zones", "booking_services", "requirements"},
            )
            self.session.add(service)
            await self.session.commit()
            await self.session.refresh(service)
            return service
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_service(
        self, service: KpEventService, update_service_input: UpdateServiceInput
    ) -> KpEventService:
        try:
            service.sqlmodel_update(update_service_input.model_dump(exclude_unset=True))
            self._validate_model(
                service,
                exclude={"event", "booth_zones", "booking_services", "requirements"},
            )
            self.session.add(service)
            await self.session.commit()
            await self.session.refresh(service)
            return service
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_service(self, service: KpEventService) -> None:
        try:
            await self.session.delete(service)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_industry(self, industry: KpIndustry) -> None:
        try:
            await self.session.delete(industry)
            await self.session.commit()
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

    async def get_company_active_booking_for_event(
        self, event_id: UUID, company_id: UUID
    ) -> Optional[KpEventBooking]:
        statement = self._booking_select().where(
            KpEventBooking.event_id == event_id,
            KpEventBooking.company_id == company_id,
            KpEventBooking.status != KpBookingStatus.CANCELLED,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def count_active_bookings_for_zone(
        self, event_id: UUID, booth_zone_id: UUID
    ) -> int:
        statement = (
            select(func.count())
            .select_from(KpEventBooking)
            .where(
                KpEventBooking.event_id == event_id,
                KpEventBooking.booth_zone_id == booth_zone_id,
                KpEventBooking.status != KpBookingStatus.CANCELLED,
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def lock_booth_zone_for_update(
        self, booth_zone_id: UUID
    ) -> Optional[KpEventBoothZone]:
        """Acquires a row-level lock on the zone row. Must be called within the
        same transaction as the subsequent capacity count check and booking creation,
        so the lock is held until commit, preventing concurrent oversubscription."""
        statement = (
            select(KpEventBoothZone)
            .where(KpEventBoothZone.id == booth_zone_id)
            .with_for_update()
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_booking(
        self,
        event_id: UUID,
        company_id: UUID,
        booth_zone_id: UUID,
        create_booking_input: CreateBookingInput,
    ) -> KpEventBooking:
        try:
            booking = KpEventBooking(
                **create_booking_input.model_dump(),
                event_id=event_id,
                company_id=company_id,
                booth_zone_id=booth_zone_id,
            )
            self._validate_booking(booking)
            self.session.add(booking)
            await self.session.commit()
            return await self.get_booking_by_id(booking.id) or booking
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_booking(
        self, booking: KpEventBooking, update_booking_input: UpdateBookingInput
    ) -> KpEventBooking:
        try:
            booking.sqlmodel_update(update_booking_input.model_dump(exclude_unset=True))
            self._validate_booking(booking)
            self.session.add(booking)
            await self.session.commit()
            return await self.get_booking_by_id(booking.id) or booking
        except Exception as e:
            await self.session.rollback()
            raise e

    async def list_booking_upgrade_waitlist_entries(
        self, booking_id: UUID
    ) -> list[KpEventBookingUpgradeWaitlist]:
        statement = (
            select(KpEventBookingUpgradeWaitlist)
            .where(KpEventBookingUpgradeWaitlist.booking_id == booking_id)
            .order_by(
                KpEventBookingUpgradeWaitlist.priority_rank.asc().nulls_last(),
                KpEventBookingUpgradeWaitlist.created_at.asc(),
            )
            .options(
                selectinload(KpEventBookingUpgradeWaitlist.target_booth_zone),
                selectinload(KpEventBookingUpgradeWaitlist.booking),
            )
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def replace_booking_upgrade_waitlist_entries(
        self,
        booking: KpEventBooking,
        target_booth_zone_ids: list[UUID],
    ) -> list[KpEventBookingUpgradeWaitlist]:
        try:
            statement = select(KpEventBookingUpgradeWaitlist).where(
                KpEventBookingUpgradeWaitlist.booking_id == booking.id
            )
            result = await self.session.execute(statement)
            existing_entries = result.scalars().all()

            for entry in existing_entries:
                await self.session.delete(entry)

            for priority_rank, target_booth_zone_id in enumerate(
                target_booth_zone_ids, start=1
            ):
                entry = KpEventBookingUpgradeWaitlist(
                    booking_id=booking.id,
                    target_booth_zone_id=target_booth_zone_id,
                    priority_rank=priority_rank,
                )
                self._validate_model(
                    entry,
                    exclude={"booking", "target_booth_zone"},
                )
                self.session.add(entry)

            await self.session.commit()
            return await self.list_booking_upgrade_waitlist_entries(booking.id)
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

    async def get_service_requirement_by_id(
        self, requirement_id: UUID
    ) -> Optional[KpEventServiceRequirement]:
        statement = (
            select(KpEventServiceRequirement)
            .where(KpEventServiceRequirement.id == requirement_id)
            .options(selectinload(KpEventServiceRequirement.service))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> Optional[KpEventBookingServiceFileLink]:
        statement = (
            select(KpEventBookingServiceFileLink)
            .where(
                KpEventBookingServiceFileLink.booking_service_id == booking_service_id,
                KpEventBookingServiceFileLink.requirement_id == requirement_id,
            )
            .options(
                selectinload(KpEventBookingServiceFileLink.requirement),
                selectinload(KpEventBookingServiceFileLink.stored_file),
                selectinload(KpEventBookingServiceFileLink.booking_service),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_booking_service_by_id(
        self, booking_service_id: UUID
    ) -> Optional[KpEventBookingService]:
        statement = (
            select(KpEventBookingService)
            .where(KpEventBookingService.id == booking_service_id)
            .options(
                selectinload(KpEventBookingService.booking),
                selectinload(KpEventBookingService.service),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_stored_file(
        self,
        storage_key: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        etag: str | None,
        stored_file: StoredFile | None = None,
    ) -> StoredFile:
        try:
            if stored_file is None:
                stored_file = StoredFile(
                    storage_key=storage_key,
                    original_filename=original_filename,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    sha256=sha256,
                    etag=etag,
                )
            else:
                stored_file.storage_key = storage_key
                stored_file.original_filename = original_filename
                stored_file.mime_type = mime_type
                stored_file.size_bytes = size_bytes
                stored_file.sha256 = sha256
                stored_file.etag = etag

            self._validate_model(stored_file)
            self.session.add(stored_file)
            await self.session.commit()
            await self.session.refresh(stored_file)
            return stored_file
        except Exception as e:
            await self.session.rollback()
            raise e

    async def upsert_requirement_file_link(
        self,
        booking_service_id: UUID,
        requirement_id: UUID,
        stored_file_id: UUID,
    ) -> KpEventBookingServiceFileLink:
        try:
            requirement_file = await self.get_requirement_file(
                booking_service_id, requirement_id
            )
            if requirement_file is None:
                requirement_file = KpEventBookingServiceFileLink(
                    booking_service_id=booking_service_id,
                    requirement_id=requirement_id,
                    stored_file_id=stored_file_id,
                )
            else:
                requirement_file.stored_file_id = stored_file_id

            self._validate_model(
                requirement_file,
                exclude={"booking_service", "requirement", "stored_file"},
            )
            self.session.add(requirement_file)
            await self.session.commit()
            await self.session.refresh(requirement_file)
            return (
                await self.get_requirement_file(booking_service_id, requirement_id)
                or requirement_file
            )
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_requirement_file_link(
        self, requirement_file: KpEventBookingServiceFileLink
    ) -> None:
        try:
            await self.session.delete(requirement_file)
            await self.session.commit()
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

    async def list_orphaned_stored_files(self, max_age_hours: int) -> list[StoredFile]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        statement = (
            select(StoredFile)
            .outerjoin(
                KpEventBookingServiceFileLink,
                KpEventBookingServiceFileLink.stored_file_id == StoredFile.id,
            )
            .where(
                and_(
                    KpEventBookingServiceFileLink.id.is_(None),
                    StoredFile.updated_at < cutoff,
                )
            )
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_industries(self) -> list[KpIndustry]:
        statement = select(KpIndustry).order_by(KpIndustry.name.asc())
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_industry_by_id(self, industry_id: UUID) -> Optional[KpIndustry]:
        return await self._get_by_field(KpIndustry.id, industry_id)

    async def get_industry_by_name(self, name: str) -> Optional[KpIndustry]:
        return await self._get_by_field(KpIndustry.name, name)

    async def create_industry(
        self, create_industry_input: CreateIndustryInput
    ) -> KpIndustry:
        try:
            industry = KpIndustry(**create_industry_input.model_dump())
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
        self, booking_id: UUID, upsert_company_details_input: UpsertCompanyDetailsInput
    ) -> KpBookingCompanyDetails:
        try:
            statement = select(KpBookingCompanyDetails).where(
                KpBookingCompanyDetails.booking_id == booking_id
            )
            result = await self.session.execute(statement)
            company_details = result.scalar_one_or_none()

            if company_details is None:
                company_details = KpBookingCompanyDetails(booking_id=booking_id)

            company_details.sqlmodel_update(
                upsert_company_details_input.model_dump(exclude_unset=True)
            )

            self.session.add(company_details)
            await self.session.commit()
            await self.session.refresh(company_details)
            return company_details
        except Exception as e:
            await self.session.rollback()
            raise e
