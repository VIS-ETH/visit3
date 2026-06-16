from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.company import Company, KpCompanyProfile
from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpBookingCompanyDetailsIndustryLink,
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBookletAssets,
    KpEventBookletExportTask,
    KpEventBookletExportTaskStatus,
    KpEventBoothZone,
    KpEventBoothZoneServiceLink,
    KpEventNametagBackground,
    KpEventRegistrationException,
    KpEventService,
    KpEventServiceRequirement,
    KpIndustry,
    NameTag,
)
from app.models.storage import StoredFile
from app.repositories.base import BaseRepository, rel
from app.schemas.kp import (
    BookingServiceInput,
    CloneKpInput,
    CreateBookingInput,
    CreateBoothZoneInput,
    CreateIndustryInput,
    CreateKpInput,
    CreateServiceInput,
    ServiceRequirementInput,
    UpdateBookingInput,
    UpdateBoothZoneInput,
    UpdateKpInput,
    UpdateServiceInput,
    UpsertCompanyDetailsInput,
)

SERVICE_CLONE_FIELDS = (
    "name",
    "description",
    "confirmation_description",
    "order",
    "price",
    "max_quantity_per_booking",
    "max_total_quantity",
    "is_active",
)

SERVICE_REQUIREMENT_CLONE_FIELDS = (
    "type",
    "name",
    "description",
    "order",
)

BOOTH_ZONE_CLONE_FIELDS = (
    "name",
    "description",
    "color",
    "order",
    "capacity",
    "booth_size",
    "base_price",
)

INCLUDED_SERVICE_CLONE_FIELDS = ("included_quantity",)


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
            selectinload(rel(KpEventBooking.event)),
            selectinload(rel(KpEventBooking.booth_zone)),
            selectinload(rel(KpEventBooking.name_tags)),
            selectinload(rel(KpEventBooking.company)).selectinload(
                rel(Company.kp_profile)
            ),
            selectinload(rel(KpEventBooking.company))
            .selectinload(rel(Company.kp_profile))
            .selectinload(rel(KpCompanyProfile.kp_contact_user)),
            selectinload(rel(KpEventBooking.company)).selectinload(rel(Company.users)),
            selectinload(rel(KpEventBooking.services))
            .selectinload(rel(KpEventBookingService.service))
            .selectinload(rel(KpEventService.requirements)),
            selectinload(rel(KpEventBooking.services))
            .selectinload(rel(KpEventBookingService.service))
            .selectinload(rel(KpEventService.image_stored_file)),
            selectinload(rel(KpEventBooking.services))
            .selectinload(rel(KpEventBookingService.requirement_file_links))
            .selectinload(rel(KpEventBookingServiceFileLink.requirement)),
            selectinload(rel(KpEventBooking.services))
            .selectinload(rel(KpEventBookingService.requirement_file_links))
            .selectinload(rel(KpEventBookingServiceFileLink.stored_file)),
            selectinload(rel(KpEventBooking.upgrade_waitlist_entries)).selectinload(
                rel(KpEventBookingUpgradeWaitlist.target_booth_zone)
            ),
            selectinload(rel(KpEventBooking.company_details))
            .selectinload(rel(KpBookingCompanyDetails.industry_links))
            .selectinload(rel(KpBookingCompanyDetailsIndustryLink.industry)),
            selectinload(rel(KpEventBooking.company_details)).selectinload(
                rel(KpBookingCompanyDetails.logo_stored_file)
            ),
        )

    async def get_by_name(self, name: str) -> Optional[KpEvent]:
        return await self._get_by_field(col(KpEvent.name), name)

    async def list_kps(self) -> Sequence[KpEvent]:
        statement = select(KpEvent).order_by(col(KpEvent.event_date).desc())
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_latest_kp(self) -> Optional[KpEvent]:
        statement = select(KpEvent).order_by(col(KpEvent.event_date).desc()).limit(1)
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

    async def clone_kp(
        self, event_id: UUID, clone_kp_input: CloneKpInput
    ) -> Optional[KpEvent]:
        try:
            statement = (
                select(KpEvent)
                .where(col(KpEvent.id) == event_id)
                .options(
                    selectinload(rel(KpEvent.services)).selectinload(
                        rel(KpEventService.requirements)
                    ),
                    selectinload(rel(KpEvent.booth_zones)).selectinload(
                        rel(KpEventBoothZone.included_services)
                    ),
                )
            )
            result = await self.session.execute(statement)
            source_event = result.scalar_one_or_none()
            if source_event is None:
                return None

            cloned_event = KpEvent(**clone_kp_input.model_dump())
            self._validate_model(
                cloned_event,
                exclude={
                    "booth_zones",
                    "bookings",
                    "services",
                    "registration_exceptions",
                    "nametag_background",
                },
            )
            self.session.add(cloned_event)

            service_id_map: dict[UUID, UUID] = {}
            for service in source_event.services:
                cloned_service = self._clone_model(
                    KpEventService,
                    service,
                    SERVICE_CLONE_FIELDS,
                    event_id=cloned_event.id,
                )
                service_id_map[service.id] = cloned_service.id

                for requirement in service.requirements:
                    self._clone_model(
                        KpEventServiceRequirement,
                        requirement,
                        SERVICE_REQUIREMENT_CLONE_FIELDS,
                        service_id=cloned_service.id,
                    )

            booth_zone_id_map: dict[UUID, UUID] = {}
            for booth_zone in source_event.booth_zones:
                cloned_booth_zone = self._clone_model(
                    KpEventBoothZone,
                    booth_zone,
                    BOOTH_ZONE_CLONE_FIELDS,
                    event_id=cloned_event.id,
                )
                booth_zone_id_map[booth_zone.id] = cloned_booth_zone.id

            for booth_zone in source_event.booth_zones:
                cloned_booth_zone_id = booth_zone_id_map[booth_zone.id]
                for included_service in booth_zone.included_services:
                    cloned_service_id = service_id_map.get(included_service.service_id)
                    if cloned_service_id is None:
                        continue
                    self._clone_model(
                        KpEventBoothZoneServiceLink,
                        included_service,
                        INCLUDED_SERVICE_CLONE_FIELDS,
                        booth_zone_id=cloned_booth_zone_id,
                        service_id=cloned_service_id,
                    )

            if source_event.advertisement_service_id is not None:
                cloned_advertisement_service_id = service_id_map.get(
                    source_event.advertisement_service_id
                )
                if cloned_advertisement_service_id is not None:
                    cloned_event.advertisement_service_id = (
                        cloned_advertisement_service_id
                    )

            await self.session.commit()
            await self.session.refresh(cloned_event)
            return cloned_event
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
            data = create_service_input.model_dump(exclude={"requirements"})
            service = KpEventService(
                **data,
                event_id=event_id,
            )
            self._validate_model(
                service,
                exclude={"event", "booth_zones", "booking_services", "requirements"},
            )
            self.session.add(service)
            await self.session.flush()
            await self._replace_service_requirements(
                service, create_service_input.requirements
            )
            await self.session.commit()
            return await self.get_service_by_id(service.id) or service
        except Exception as e:
            await self.session.rollback()
            raise e

    async def _replace_service_requirements(
        self,
        service: KpEventService,
        requirements: list[ServiceRequirementInput],
    ) -> None:
        statement = select(KpEventServiceRequirement).where(
            col(KpEventServiceRequirement.service_id) == service.id
        )
        result = await self.session.execute(statement)
        existing_requirements = result.scalars().all()
        existing_by_id = {
            requirement.id: requirement for requirement in existing_requirements
        }
        kept_ids: set[UUID] = set()

        for requirement_input in requirements:
            requirement = (
                existing_by_id.get(requirement_input.id)
                if requirement_input.id is not None
                else None
            )
            data = requirement_input.model_dump(exclude={"id"})
            if requirement is None:
                requirement = KpEventServiceRequirement(service_id=service.id, **data)
            else:
                kept_ids.add(requirement.id)
                requirement.sqlmodel_update(data)

            self._validate_model(requirement, exclude={"service"})
            self.session.add(requirement)

        for requirement in existing_requirements:
            if requirement.id not in kept_ids:
                await self.session.delete(requirement)

    async def update_service(
        self, service: KpEventService, update_service_input: UpdateServiceInput
    ) -> KpEventService:
        try:
            updates = update_service_input.model_dump(
                exclude_unset=True, exclude={"requirements"}
            )
            service.sqlmodel_update(updates)
            self._validate_model(
                service,
                exclude={"event", "booth_zones", "booking_services", "requirements"},
            )
            self.session.add(service)
            if update_service_input.requirements is not None:
                await self._replace_service_requirements(
                    service, update_service_input.requirements
                )
            await self.session.commit()
            return await self.get_service_by_id(service.id) or service
        except Exception as e:
            await self.session.rollback()
            raise e

    async def set_service_image_stored_file_id(
        self, service: KpEventService, stored_file_id: UUID | None
    ) -> KpEventService:
        try:
            service.image_stored_file_id = stored_file_id
            self.session.add(service)
            await self.session.commit()
            return await self.get_service_by_id(service.id) or service
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
        statement = self._booking_select().where(col(KpEventBooking.id) == booking_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_name_tag_by_id(self, name_tag_id: UUID) -> Optional[NameTag]:
        statement = (
            select(NameTag)
            .where(col(NameTag.id) == name_tag_id)
            .options(
                selectinload(rel(NameTag.booking)).selectinload(
                    rel(KpEventBooking.company)
                ),
                selectinload(rel(NameTag.booking)).selectinload(
                    rel(KpEventBooking.event)
                ),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_name_tags_for_event(self, event_id: UUID) -> Sequence[NameTag]:
        statement = (
            select(NameTag)
            .join(KpEventBooking)
            .where(col(KpEventBooking.event_id) == event_id)
            .options(
                selectinload(rel(NameTag.booking)).selectinload(
                    rel(KpEventBooking.company)
                ),
                selectinload(rel(NameTag.booking)).selectinload(
                    rel(KpEventBooking.event)
                ),
            )
            .order_by(col(NameTag.last_name).asc(), col(NameTag.first_name).asc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_name_tags_for_booking(self, booking_id: UUID) -> Sequence[NameTag]:
        statement = (
            select(NameTag)
            .where(col(NameTag.booking_id) == booking_id)
            .options(
                selectinload(rel(NameTag.booking)).selectinload(
                    rel(KpEventBooking.company)
                ),
                selectinload(rel(NameTag.booking)).selectinload(
                    rel(KpEventBooking.event)
                ),
            )
            .order_by(col(NameTag.last_name).asc(), col(NameTag.first_name).asc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_bookings_for_event(self, event_id: UUID) -> Sequence[KpEventBooking]:
        statement = self._booking_select().where(
            col(KpEventBooking.event_id) == event_id
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

    async def get_company_active_booking_for_event(
        self, event_id: UUID, company_id: UUID
    ) -> Optional[KpEventBooking]:
        statement = self._booking_select().where(
            col(KpEventBooking.event_id) == event_id,
            col(KpEventBooking.company_id) == company_id,
            col(KpEventBooking.status) != KpBookingStatus.CANCELLED,
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
                col(KpEventBooking.event_id) == event_id,
                col(KpEventBooking.booth_zone_id) == booth_zone_id,
                col(KpEventBooking.status) != KpBookingStatus.CANCELLED,
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def count_active_service_quantity(self, service_id: UUID) -> int:
        statement = (
            select(func.coalesce(func.sum(KpEventBookingService.quantity), 0))
            .join(KpEventBooking)
            .where(
                col(KpEventBookingService.service_id) == service_id,
                col(KpEventBooking.status) != KpBookingStatus.CANCELLED,
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def _validate_services_for_booking(
        self,
        event_id: UUID,
        services: Sequence[BookingServiceInput],
        existing_services: Sequence[KpEventBookingService] = (),
    ) -> list[BookingServiceInput]:
        """Lock services and validate quantities inside the current transaction."""
        from app.core.exceptions import (
            KpServiceQuantityInvalid,
            KpServiceUnavailable,
        )

        existing_quantities = {
            booking_service.service_id: booking_service.quantity
            for booking_service in existing_services
        }
        service_quantities: dict[UUID, int] = {}
        for booking_service in services:
            service_quantities[booking_service.service_id] = (
                service_quantities.get(booking_service.service_id, 0)
                + booking_service.quantity
            )

        validated_services: list[BookingServiceInput] = []
        for service_id, quantity in service_quantities.items():
            statement = (
                select(KpEventService)
                .where(col(KpEventService.id) == service_id)
                .with_for_update()
            )
            result = await self.session.execute(statement)
            service = result.scalar_one_or_none()
            if service is None:
                raise KpServiceUnavailable(
                    f"create_booking:service_not_found:{service_id}"
                )
            if service.event_id != event_id or not service.is_active:
                raise KpServiceUnavailable(
                    f"create_booking:service_unavailable:{service_id}"
                )
            total_booking_quantity = existing_quantities.get(service_id, 0) + quantity
            if total_booking_quantity > service.max_quantity_per_booking:
                raise KpServiceQuantityInvalid(
                    "create_booking:service_max_per_booking:"
                    f"{service_id}:{total_booking_quantity}"
                )
            if service.max_total_quantity > 0:
                booked_quantity = await self.count_active_service_quantity(service_id)
                if booked_quantity + quantity > service.max_total_quantity:
                    raise KpServiceQuantityInvalid(
                        f"create_booking:service_max_total:{service_id}:{quantity}"
                    )
            validated_services.append(
                BookingServiceInput(service_id=service_id, quantity=quantity)
            )
        return validated_services

    async def create_booking(
        self,
        event_id: UUID,
        company_id: UUID,
        booth_zone_id: UUID,
        create_booking_input: CreateBookingInput,
        services: Sequence[BookingServiceInput] = (),
        included_services: Sequence[KpEventBoothZoneServiceLink] = (),
    ) -> KpEventBooking:
        try:
            await self._validate_services_for_booking(event_id, services)

            booking = KpEventBooking(
                **create_booking_input.model_dump(),
                event_id=event_id,
                company_id=company_id,
                booth_zone_id=booth_zone_id,
            )
            self._validate_booking(booking)
            self.session.add(booking)
            await self.session.flush()

            booking_services_by_service_id = {
                item.service_id: KpEventBookingService(
                    booking_id=booking.id,
                    service_id=item.service_id,
                    quantity=item.quantity,
                    included_quantity=0,
                )
                for item in services
            }
            for included_service in included_services:
                booking_service = booking_services_by_service_id.get(
                    included_service.service_id
                )
                if booking_service is None:
                    booking_service = KpEventBookingService(
                        booking_id=booking.id,
                        service_id=included_service.service_id,
                        quantity=included_service.included_quantity,
                    )
                    booking_services_by_service_id[included_service.service_id] = (
                        booking_service
                    )
                else:
                    booking_service.quantity += included_service.included_quantity
                booking_service.included_quantity = included_service.included_quantity

            for booking_service in booking_services_by_service_id.values():
                self._validate_model(
                    booking_service,
                    exclude={"booking", "service", "requirement_file_links"},
                )
                self.session.add(booking_service)

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

    async def add_booking_services(
        self,
        booking: KpEventBooking,
        services: Sequence[BookingServiceInput],
    ) -> KpEventBooking:
        try:
            await self._validate_services_for_booking(
                booking.event_id, services, booking.services
            )

            service_ids = [item.service_id for item in services]
            existing_by_service_id: dict[UUID, KpEventBookingService] = {}
            if service_ids:
                statement = select(KpEventBookingService).where(
                    col(KpEventBookingService.booking_id) == booking.id,
                    col(KpEventBookingService.service_id).in_(service_ids),
                )
                result = await self.session.execute(statement)
                existing_by_service_id = {
                    booking_service.service_id: booking_service
                    for booking_service in result.scalars().all()
                }

            for item in services:
                booking_service = existing_by_service_id.get(item.service_id)
                if booking_service is None:
                    booking_service = KpEventBookingService(
                        booking_id=booking.id,
                        service_id=item.service_id,
                        quantity=item.quantity,
                        included_quantity=0,
                    )
                    existing_by_service_id[item.service_id] = booking_service
                else:
                    booking_service.quantity += item.quantity

                self._validate_model(
                    booking_service,
                    exclude={"booking", "service", "requirement_file_links"},
                )
                self.session.add(booking_service)

            await self.session.commit()
            return await self.get_booking_by_id(booking.id) or booking
        except Exception as e:
            await self.session.rollback()
            raise e

    async def list_booking_upgrade_waitlist_entries(
        self, booking_id: UUID
    ) -> Sequence[KpEventBookingUpgradeWaitlist]:
        statement = (
            select(KpEventBookingUpgradeWaitlist)
            .where(col(KpEventBookingUpgradeWaitlist.booking_id) == booking_id)
            .order_by(
                col(KpEventBookingUpgradeWaitlist.priority_rank).asc().nulls_last(),
                col(KpEventBookingUpgradeWaitlist.created_at).asc(),
            )
            .options(
                selectinload(rel(KpEventBookingUpgradeWaitlist.target_booth_zone)),
                selectinload(rel(KpEventBookingUpgradeWaitlist.booking)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def replace_booking_upgrade_waitlist_entries(
        self,
        booking: KpEventBooking,
        target_booth_zone_ids: list[UUID],
    ) -> Sequence[KpEventBookingUpgradeWaitlist]:
        try:
            statement = select(KpEventBookingUpgradeWaitlist).where(
                col(KpEventBookingUpgradeWaitlist.booking_id) == booking.id
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

    async def list_booth_zones(self, event_id: UUID) -> Sequence[KpEventBoothZone]:
        statement = (
            select(KpEventBoothZone)
            .where(col(KpEventBoothZone.event_id) == event_id)
            .order_by(
                col(KpEventBoothZone.order).asc(), col(KpEventBoothZone.name).asc()
            )
            .options(selectinload(rel(KpEventBoothZone.included_services)))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_booth_zone_by_id(
        self, booth_zone_id: UUID
    ) -> Optional[KpEventBoothZone]:
        statement = (
            select(KpEventBoothZone)
            .where(col(KpEventBoothZone.id) == booth_zone_id)
            .options(selectinload(rel(KpEventBoothZone.included_services)))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_booth_zone_by_name(
        self, event_id: UUID, name: str
    ) -> Optional[KpEventBoothZone]:
        statement = (
            select(KpEventBoothZone)
            .where(
                col(KpEventBoothZone.event_id) == event_id,
                col(KpEventBoothZone.name) == name,
            )
            .options(selectinload(rel(KpEventBoothZone.included_services)))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_services(self, event_id: UUID) -> Sequence[KpEventService]:
        statement = (
            select(KpEventService)
            .where(col(KpEventService.event_id) == event_id)
            .order_by(col(KpEventService.order).asc(), col(KpEventService.name).asc())
            .options(
                selectinload(rel(KpEventService.requirements)),
                selectinload(rel(KpEventService.image_stored_file)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_service_by_id(self, service_id: UUID) -> Optional[KpEventService]:
        statement = (
            select(KpEventService)
            .where(col(KpEventService.id) == service_id)
            .options(
                selectinload(rel(KpEventService.requirements)),
                selectinload(rel(KpEventService.image_stored_file)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_service_by_name(
        self, event_id: UUID, name: str
    ) -> Optional[KpEventService]:
        statement = (
            select(KpEventService)
            .where(
                col(KpEventService.event_id) == event_id,
                col(KpEventService.name) == name,
            )
            .options(
                selectinload(rel(KpEventService.requirements)),
                selectinload(rel(KpEventService.image_stored_file)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_service_requirement_by_id(
        self, requirement_id: UUID
    ) -> Optional[KpEventServiceRequirement]:
        statement = (
            select(KpEventServiceRequirement)
            .where(col(KpEventServiceRequirement.id) == requirement_id)
            .options(selectinload(rel(KpEventServiceRequirement.service)))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> Optional[KpEventBookingServiceFileLink]:
        statement = (
            select(KpEventBookingServiceFileLink)
            .where(
                col(KpEventBookingServiceFileLink.booking_service_id)
                == booking_service_id,
                col(KpEventBookingServiceFileLink.requirement_id) == requirement_id,
            )
            .options(
                selectinload(rel(KpEventBookingServiceFileLink.requirement)),
                selectinload(rel(KpEventBookingServiceFileLink.stored_file)),
                selectinload(rel(KpEventBookingServiceFileLink.booking_service)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_booking_service_by_id(
        self, booking_service_id: UUID
    ) -> Optional[KpEventBookingService]:
        statement = (
            select(KpEventBookingService)
            .where(col(KpEventBookingService.id) == booking_service_id)
            .options(
                selectinload(rel(KpEventBookingService.booking)),
                selectinload(rel(KpEventBookingService.service)),
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
                requirement_file.text_value = None

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

    async def upsert_requirement_text_answer(
        self,
        booking_service_id: UUID,
        requirement_id: UUID,
        text_value: str,
    ) -> KpEventBookingServiceFileLink:
        try:
            requirement_answer = await self.get_requirement_file(
                booking_service_id, requirement_id
            )
            if requirement_answer is None:
                requirement_answer = KpEventBookingServiceFileLink(
                    booking_service_id=booking_service_id,
                    requirement_id=requirement_id,
                    text_value=text_value,
                )
            else:
                requirement_answer.stored_file_id = None
                requirement_answer.text_value = text_value

            self._validate_model(
                requirement_answer,
                exclude={"booking_service", "requirement", "stored_file"},
            )
            self.session.add(requirement_answer)
            await self.session.commit()
            await self.session.refresh(requirement_answer)
            return (
                await self.get_requirement_file(booking_service_id, requirement_id)
                or requirement_answer
            )
        except Exception as e:
            await self.session.rollback()
            raise e

    async def set_advertisement_service_id(
        self, event: KpEvent, service_id: UUID | None
    ) -> KpEvent:
        try:
            event.advertisement_service_id = service_id
            self.session.add(event)
            await self.session.commit()
            await self.session.refresh(event)
            return event
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_nametag_background(
        self, event_id: UUID
    ) -> Optional[KpEventNametagBackground]:
        statement = (
            select(KpEventNametagBackground)
            .where(col(KpEventNametagBackground.event_id) == event_id)
            .options(
                selectinload(rel(KpEventNametagBackground.event)),
                selectinload(rel(KpEventNametagBackground.stored_file)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_nametag_background(
        self,
        event_id: UUID,
        stored_file_id: UUID,
    ) -> KpEventNametagBackground:
        try:
            statement = (
                select(KpEventNametagBackground)
                .where(col(KpEventNametagBackground.event_id) == event_id)
                .with_for_update()
            )
            result = await self.session.execute(statement)
            background = result.scalar_one_or_none()
            if background is None:
                background = KpEventNametagBackground(
                    event_id=event_id,
                    stored_file_id=stored_file_id,
                )
            else:
                background.stored_file_id = stored_file_id

            self._validate_model(background, exclude={"event", "stored_file"})
            self.session.add(background)
            await self.session.commit()
            return await self.get_nametag_background(event_id) or background
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

    async def list_orphaned_stored_files(
        self, max_age_hours: int
    ) -> Sequence[StoredFile]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        statement = (
            select(StoredFile)
            .outerjoin(
                KpEventBookingServiceFileLink,
                col(KpEventBookingServiceFileLink.stored_file_id) == col(StoredFile.id),
            )
            .outerjoin(
                KpEventNametagBackground,
                col(KpEventNametagBackground.stored_file_id) == col(StoredFile.id),
            )
            .outerjoin(
                KpEventService,
                col(KpEventService.image_stored_file_id) == col(StoredFile.id),
            )
            .outerjoin(
                KpEventBookletAssets,
                (
                    col(KpEventBookletAssets.intro_page_stored_file_id)
                    == col(StoredFile.id)
                )
                | (
                    col(KpEventBookletAssets.blank_page_stored_file_id)
                    == col(StoredFile.id)
                )
                | (
                    col(KpEventBookletAssets.missing_advertisement_stored_file_id)
                    == col(StoredFile.id)
                ),
            )
            .outerjoin(
                KpEventBookletExportTask,
                col(KpEventBookletExportTask.output_stored_file_id)
                == col(StoredFile.id),
            )
            .outerjoin(
                KpBookingCompanyDetails,
                col(KpBookingCompanyDetails.logo_stored_file_id) == col(StoredFile.id),
            )
            .where(
                and_(
                    col(KpEventBookingServiceFileLink.id).is_(None),
                    col(KpEventNametagBackground.id).is_(None),
                    col(KpEventService.id).is_(None),
                    col(KpEventBookletAssets.id).is_(None),
                    col(KpEventBookletExportTask.id).is_(None),
                    col(KpBookingCompanyDetails.id).is_(None),
                    col(StoredFile.updated_at) < cutoff,
                )
            )
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_industries(self) -> Sequence[KpIndustry]:
        statement = select(KpIndustry).order_by(col(KpIndustry.name).asc())
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_industry_by_id(self, industry_id: UUID) -> Optional[KpIndustry]:
        statement = select(KpIndustry).where(col(KpIndustry.id) == industry_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_industries_by_ids(
        self, industry_ids: Sequence[UUID]
    ) -> Sequence[KpIndustry]:
        if not industry_ids:
            return []
        statement = select(KpIndustry).where(col(KpIndustry.id).in_(industry_ids))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_industry_by_name(self, name: str) -> Optional[KpIndustry]:
        statement = select(KpIndustry).where(col(KpIndustry.name) == name)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

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
    ) -> Sequence[KpEventRegistrationException]:
        statement = (
            select(KpEventRegistrationException)
            .where(col(KpEventRegistrationException.event_id) == event_id)
            .options(selectinload(rel(KpEventRegistrationException.company)))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_registration_exception(
        self, event_id: UUID, company_id: UUID
    ) -> Optional[KpEventRegistrationException]:
        statement = select(KpEventRegistrationException).where(
            col(KpEventRegistrationException.event_id) == event_id,
            col(KpEventRegistrationException.company_id) == company_id,
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

    async def get_company_details_by_booking_id(
        self, booking_id: UUID
    ) -> Optional[KpBookingCompanyDetails]:
        statement = (
            select(KpBookingCompanyDetails)
            .where(col(KpBookingCompanyDetails.booking_id) == booking_id)
            .options(
                selectinload(rel(KpBookingCompanyDetails.industry_links)).selectinload(
                    rel(KpBookingCompanyDetailsIndustryLink.industry)
                ),
                selectinload(rel(KpBookingCompanyDetails.logo_stored_file)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_company_details(
        self,
        booking_id: UUID,
        upsert_company_details_input: UpsertCompanyDetailsInput,
        industry_ids: Sequence[UUID],
    ) -> KpBookingCompanyDetails:
        try:
            company_details = await self.get_company_details_by_booking_id(booking_id)

            if company_details is None:
                company_details = KpBookingCompanyDetails(booking_id=booking_id)

            company_details.sqlmodel_update(
                upsert_company_details_input.model_dump(
                    exclude={"industry_ids"}, exclude_unset=True
                )
            )

            self.session.add(company_details)
            await self.session.flush()

            existing_links_statement = select(
                KpBookingCompanyDetailsIndustryLink
            ).where(
                col(KpBookingCompanyDetailsIndustryLink.booking_company_details_id)
                == company_details.id
            )
            existing_links = (
                await self.session.execute(existing_links_statement)
            ).scalars()
            for link in existing_links:
                await self.session.delete(link)

            for industry_id in industry_ids:
                self.session.add(
                    KpBookingCompanyDetailsIndustryLink(
                        booking_company_details_id=company_details.id,
                        industry_id=industry_id,
                    )
                )

            await self.session.commit()
            return (
                await self.get_company_details_by_booking_id(booking_id)
                or company_details
            )
        except Exception as e:
            await self.session.rollback()
            raise e

    # --- Booklet Assets ---

    async def get_booklet_assets(
        self, event_id: UUID
    ) -> Optional[KpEventBookletAssets]:
        statement = (
            select(KpEventBookletAssets)
            .where(col(KpEventBookletAssets.event_id) == event_id)
            .options(
                selectinload(rel(KpEventBookletAssets.intro_page_stored_file)),
                selectinload(rel(KpEventBookletAssets.blank_page_stored_file)),
                selectinload(
                    rel(KpEventBookletAssets.missing_advertisement_stored_file)
                ),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_booklet_asset_file(
        self,
        event_id: UUID,
        field_name: str,
        stored_file_id: UUID | None,
    ) -> KpEventBookletAssets:
        try:
            statement = (
                select(KpEventBookletAssets)
                .where(col(KpEventBookletAssets.event_id) == event_id)
                .with_for_update()
            )
            result = await self.session.execute(statement)
            assets = result.scalar_one_or_none()
            if assets is None:
                assets = KpEventBookletAssets(event_id=event_id)
            setattr(assets, field_name, stored_file_id)
            self.session.add(assets)
            await self.session.commit()
            return await self.get_booklet_assets(event_id) or assets
        except Exception as e:
            await self.session.rollback()
            raise e

    async def set_company_details_logo_stored_file_id(
        self,
        details: KpBookingCompanyDetails,
        stored_file_id: UUID | None,
    ) -> KpBookingCompanyDetails:
        try:
            statement = (
                select(KpBookingCompanyDetails)
                .where(col(KpBookingCompanyDetails.id) == details.id)
                .with_for_update()
            )
            result = await self.session.execute(statement)
            locked_details = result.scalar_one()
            locked_details.logo_stored_file_id = stored_file_id
            self.session.add(locked_details)
            await self.session.commit()
            return (
                await self.get_company_details_by_booking_id(details.booking_id)
                or locked_details
            )
        except Exception as e:
            await self.session.rollback()
            raise e

    # --- Booklet Export Tasks ---

    async def create_booklet_export_task(
        self, event_id: UUID
    ) -> KpEventBookletExportTask:
        try:
            task = KpEventBookletExportTask(event_id=event_id)
            self.session.add(task)
            await self.session.commit()
            return await self.get_booklet_export_task(task.id) or task
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_booklet_export_task(
        self, task_id: UUID
    ) -> Optional[KpEventBookletExportTask]:
        statement = (
            select(KpEventBookletExportTask)
            .where(col(KpEventBookletExportTask.id) == task_id)
            .options(
                selectinload(rel(KpEventBookletExportTask.output_stored_file)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_booklet_export_tasks(
        self, event_id: UUID, limit: int = 20
    ) -> Sequence[KpEventBookletExportTask]:
        statement = (
            select(KpEventBookletExportTask)
            .where(col(KpEventBookletExportTask.event_id) == event_id)
            .options(
                selectinload(rel(KpEventBookletExportTask.output_stored_file)),
            )
            .order_by(col(KpEventBookletExportTask.created_at).desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def claim_next_pending_booklet_export_task(
        self,
    ) -> Optional[KpEventBookletExportTask]:
        """
        Atomically picks the oldest PENDING task and flips it to RUNNING.
        Uses FOR UPDATE SKIP LOCKED so multiple workers don't collide.
        Returns None if no PENDING tasks remain.
        """
        try:
            statement = (
                select(KpEventBookletExportTask)
                .where(
                    col(KpEventBookletExportTask.status)
                    == KpEventBookletExportTaskStatus.PENDING
                )
                .order_by(col(KpEventBookletExportTask.created_at).asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            result = await self.session.execute(statement)
            task = result.scalar_one_or_none()
            if task is None:
                await self.session.commit()
                return None
            task.status = KpEventBookletExportTaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.session.add(task)
            await self.session.commit()
            return await self.get_booklet_export_task(task.id)
        except Exception as e:
            await self.session.rollback()
            raise e

    async def mark_orphan_running_booklet_export_tasks_as_failed(
        self, max_age_seconds: float = 300
    ) -> int:
        """Called on app startup: mark RUNNING tasks older than max_age_seconds as failed."""
        try:
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                seconds=max_age_seconds
            )
            statement = select(KpEventBookletExportTask).where(
                col(KpEventBookletExportTask.status)
                == KpEventBookletExportTaskStatus.RUNNING,
                col(KpEventBookletExportTask.started_at) < cutoff,
            )
            result = await self.session.execute(statement)
            tasks = result.scalars().all()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            for task in tasks:
                task.status = KpEventBookletExportTaskStatus.FAILED
                task.error = "abandoned:process_restart"
                task.finished_at = now
                self.session.add(task)
            await self.session.commit()
            return len(tasks)
        except Exception as e:
            await self.session.rollback()
            raise e

    async def complete_booklet_export_task(
        self,
        task: KpEventBookletExportTask,
        output_stored_file_id: UUID,
    ) -> KpEventBookletExportTask:
        try:
            task.status = KpEventBookletExportTaskStatus.COMPLETED
            task.output_stored_file_id = output_stored_file_id
            task.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            task.error = None
            self.session.add(task)
            await self.session.commit()
            return await self.get_booklet_export_task(task.id) or task
        except Exception as e:
            await self.session.rollback()
            raise e

    async def fail_booklet_export_task(
        self,
        task: KpEventBookletExportTask,
        error: str,
    ) -> KpEventBookletExportTask:
        try:
            task.status = KpEventBookletExportTaskStatus.FAILED
            task.error = error
            task.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.session.add(task)
            await self.session.commit()
            return await self.get_booklet_export_task(task.id) or task
        except Exception as e:
            await self.session.rollback()
            raise e
