from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.core.deleted_filter import include_deleted_for
from app.models.company import Company, KpCompanyProfile
from app.models.industry import Industry, KpCompanyProfileIndustryLink
from app.models.kp_event import (
    INACTIVE_BOOKING_STATUSES,
    KpBookingCompanyDetails,
    KpBookingCompanyDetailsIndustryLink,
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventBoothZoneServiceLink,
    KpEventNametagBackground,
    KpEventRegistrationException,
    KpEventService,
    KpEventServiceRequirement,
    KpServiceCategory,
    NameTag,
)
from app.models.storage import StoredFile
from app.models.venue import KpVenueBooth, KpVenueLayout, KpVenueZoneShape
from app.repositories.base import BaseRepository, rel
from app.schemas.kp import (
    BookingServiceInput,
    CloneKpInput,
    CreateBookingInput,
    CreateBoothZoneInput,
    CreateKpInput,
    CreateServiceInput,
    IncludedServiceInput,
    NameTagInput,
    ServiceRequirementInput,
    UpdateBookingInput,
    UpdateBoothZoneInput,
    UpdateKpInput,
    UpdateServiceInput,
    kp_event_columns,
)

SERVICE_CLONE_FIELDS = (
    "name",
    "description",
    "category",
    "unit_label",
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
    "layout_description",
)

INCLUDED_SERVICE_CLONE_FIELDS = ("included_quantity",)

COMPANY_SNAPSHOT_FIELDS = (
    "description",
    "website",
    "brand_name",
    "general_email",
    "general_phone",
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

VENUE_LAYOUT_CLONE_FIELDS = (
    "name",
    "order",
    "width",
    "height",
    "is_active",
)

VENUE_ZONE_SHAPE_CLONE_FIELDS = (
    "shape",
    "label_position",
)

VENUE_BOOTH_CLONE_FIELDS = (
    "booth_nr",
    "x",
    "y",
    "rotation",
)


def _booth_zone_options() -> tuple[Any, ...]:
    return (
        selectinload(rel(KpEventBoothZone.included_services)),
        selectinload(rel(KpEventBoothZone.layout_stored_file)),
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
        statement = select(KpEventBooking).options(
            selectinload(rel(KpEventBooking.event)),
            selectinload(rel(KpEventBooking.booth_zone)).selectinload(
                rel(KpEventBoothZone.included_services)
            ),
            selectinload(rel(KpEventBooking.booth_zone)).selectinload(
                rel(KpEventBoothZone.layout_stored_file)
            ),
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
            selectinload(rel(KpEventBooking.upgrade_waitlist_entries))
            .selectinload(rel(KpEventBookingUpgradeWaitlist.target_booth_zone))
            .selectinload(rel(KpEventBoothZone.included_services)),
            selectinload(rel(KpEventBooking.upgrade_waitlist_entries))
            .selectinload(rel(KpEventBookingUpgradeWaitlist.target_booth_zone))
            .selectinload(rel(KpEventBoothZone.layout_stored_file)),
            selectinload(rel(KpEventBooking.company_details))
            .selectinload(rel(KpBookingCompanyDetails.industry_links))
            .selectinload(rel(KpBookingCompanyDetailsIndustryLink.industry)),
        )
        return include_deleted_for(
            statement.execution_options(populate_existing=True),
            KpEventBoothZone,
            Company,
            KpEventService,
            KpEventServiceRequirement,
            Industry,
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
            event = KpEvent(**kp_event_columns(create_kp_input.model_dump()))
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
            event.sqlmodel_update(
                kp_event_columns(update_kp_input.model_dump(exclude_unset=True))
            )
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

            cloned_event = KpEvent(**kp_event_columns(clone_kp_input.model_dump()))
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

            await self._clone_venue_layouts(
                source_event.id, cloned_event.id, booth_zone_id_map
            )

            await self.session.commit()
            await self.session.refresh(cloned_event)
            return cloned_event
        except Exception as e:
            await self.session.rollback()
            raise e

    async def _clone_venue_layouts(
        self,
        source_event_id: UUID,
        cloned_event_id: UUID,
        booth_zone_id_map: dict[UUID, UUID],
    ) -> None:
        statement = (
            select(KpVenueLayout)
            .where(col(KpVenueLayout.event_id) == source_event_id)
            .options(
                selectinload(rel(KpVenueLayout.zone_shapes)),
                selectinload(rel(KpVenueLayout.booths)),
            )
        )
        result = await self.session.execute(statement)
        for layout in result.scalars().all():
            cloned_layout = self._clone_model(
                KpVenueLayout,
                layout,
                VENUE_LAYOUT_CLONE_FIELDS,
                event_id=cloned_event_id,
            )
            for shape in layout.zone_shapes:
                cloned_zone_id = booth_zone_id_map.get(shape.booth_zone_id)
                if cloned_zone_id is None:
                    continue
                self._clone_model(
                    KpVenueZoneShape,
                    shape,
                    VENUE_ZONE_SHAPE_CLONE_FIELDS,
                    layout_id=cloned_layout.id,
                    booth_zone_id=cloned_zone_id,
                )
            for booth in layout.booths:
                cloned_zone_id = booth_zone_id_map.get(booth.booth_zone_id)
                if cloned_zone_id is None:
                    continue
                self._clone_model(
                    KpVenueBooth,
                    booth,
                    VENUE_BOOTH_CLONE_FIELDS,
                    layout_id=cloned_layout.id,
                    booth_zone_id=cloned_zone_id,
                )

    async def create_booth_zone(
        self, event_id: UUID, create_booth_zone_input: CreateBoothZoneInput
    ) -> KpEventBoothZone:
        try:
            zone = KpEventBoothZone(
                **create_booth_zone_input.model_dump(exclude={"included_services"}),
                event_id=event_id,
            )
            self._validate_zone(zone)
            self.session.add(zone)
            await self.session.flush()
            await self._replace_included_services(
                zone, create_booth_zone_input.included_services
            )
            await self.session.commit()
            return await self._reload_booth_zone(zone.id)
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_booth_zone(
        self, zone: KpEventBoothZone, update_booth_zone_input: UpdateBoothZoneInput
    ) -> KpEventBoothZone:
        try:
            zone.sqlmodel_update(
                update_booth_zone_input.model_dump(
                    exclude_unset=True, exclude={"included_services"}
                )
            )
            self._validate_zone(zone)
            self.session.add(zone)
            if update_booth_zone_input.included_services is not None:
                await self._replace_included_services(
                    zone, update_booth_zone_input.included_services
                )
            await self.session.commit()
            return await self._reload_booth_zone(zone.id)
        except Exception as e:
            await self.session.rollback()
            raise e

    def _validate_zone(self, zone: KpEventBoothZone) -> None:
        self._validate_model(
            zone,
            exclude={
                "event",
                "layout_stored_file",
                "included_services",
                "bookings",
                "upgrade_waitlist_entries",
            },
        )

    async def _replace_included_services(
        self,
        zone: KpEventBoothZone,
        included_services: Sequence[IncludedServiceInput],
    ) -> None:
        statement = select(KpEventBoothZoneServiceLink).where(
            col(KpEventBoothZoneServiceLink.booth_zone_id) == zone.id
        )
        result = await self.session.execute(statement)
        removed = {link.service_id: link for link in result.scalars().all()}

        for included_service in included_services:
            link = removed.pop(
                included_service.service_id, None
            ) or KpEventBoothZoneServiceLink(
                booth_zone_id=zone.id,
                service_id=included_service.service_id,
            )
            link.included_quantity = included_service.included_quantity
            self._validate_model(link, exclude={"booth_zone", "service"})
            self.session.add(link)

        for link in removed.values():
            await self.session.delete(link)

    async def set_booth_zone_layout_stored_file_id(
        self, zone: KpEventBoothZone, stored_file_id: UUID | None
    ) -> KpEventBoothZone:
        try:
            zone.layout_stored_file_id = stored_file_id
            self.session.add(zone)
            await self.session.commit()
            return await self._reload_booth_zone(zone.id)
        except Exception as e:
            await self.session.rollback()
            raise e

    async def _reload_booth_zone(self, booth_zone_id: UUID) -> KpEventBoothZone:
        statement = (
            select(KpEventBoothZone)
            .where(col(KpEventBoothZone.id) == booth_zone_id)
            .options(*_booth_zone_options())
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def delete_booth_zone(self, zone: KpEventBoothZone) -> None:
        try:
            await self.hard_delete_where(
                KpEventBoothZoneServiceLink,
                col(KpEventBoothZoneServiceLink.booth_zone_id) == zone.id,
            )
            await self.hard_delete_where(
                KpEventBookingUpgradeWaitlist,
                col(KpEventBookingUpgradeWaitlist.target_booth_zone_id) == zone.id,
            )
            await self.delete_where(
                KpVenueZoneShape, col(KpVenueZoneShape.booth_zone_id) == zone.id
            )
            await self.delete_where(
                KpVenueBooth, col(KpVenueBooth.booth_zone_id) == zone.id
            )
            zone.layout_stored_file_id = None
            self.delete(zone)
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
            await self.hard_delete_where(
                KpEventBoothZoneServiceLink,
                col(KpEventBoothZoneServiceLink.service_id) == service.id,
            )
            await self.delete_where(
                KpEventServiceRequirement,
                col(KpEventServiceRequirement.service_id) == service.id,
            )
            service.image_stored_file_id = None
            self.delete(service)
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

    async def get_company_active_booking_for_event(
        self, event_id: UUID, company_id: UUID
    ) -> Optional[KpEventBooking]:
        statement = self._booking_select().where(
            col(KpEventBooking.event_id) == event_id,
            col(KpEventBooking.company_id) == company_id,
            col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES),
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
            col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES),
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
                col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES),
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
                col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES),
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
                col(KpEventBooking.status).notin_(INACTIVE_BOOKING_STATUSES),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

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
        included_services: Sequence[KpEventBoothZoneServiceLink] = (),
        company_profile: Optional[KpCompanyProfile] = None,
        confirmed_at: Optional[datetime] = None,
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
            await self.session.flush()

            if company_profile is not None:
                self._add_company_snapshot(
                    booking.id,
                    company_profile,
                    confirmed_at or datetime.now(timezone.utc),
                )

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
                booking_service.included_quantity = included_service.included_quantity
                booking_service.quantity = max(
                    booking_service.quantity, included_service.included_quantity
                )

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

    async def move_booking_to_zone(
        self,
        booking: KpEventBooking,
        zone: KpEventBoothZone,
        *,
        clear_whole_waitlist: bool,
    ) -> KpEventBooking:
        try:
            booking.booth_zone_id = zone.id
            booking.booth_nr = None
            self._validate_booking(booking)
            self.session.add(booking)

            conditions = [col(KpEventBookingUpgradeWaitlist.booking_id) == booking.id]
            if not clear_whole_waitlist:
                conditions.append(
                    col(KpEventBookingUpgradeWaitlist.target_booth_zone_id) == zone.id
                )
            await self.hard_delete_where(KpEventBookingUpgradeWaitlist, *conditions)
            await self.session.flush()
        except Exception as e:
            await self.session.rollback()
            raise e
        return await self.apply_zone_inclusions(booking, zone)

    async def delete_booking(self, booking: KpEventBooking) -> None:
        try:
            self.delete(booking)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def acknowledge_booking_additions(
        self, booking: KpEventBooking
    ) -> KpEventBooking:
        try:
            for booking_service in booking.services:
                booking_service.added_after_confirmation = 0
                self.session.add(booking_service)
            await self.session.commit()
            return await self.get_booking_by_id(booking.id) or booking
        except Exception as e:
            await self.session.rollback()
            raise e

    async def set_booking_service_quantities(
        self,
        booking: KpEventBooking,
        quantities: dict[UUID, int],
    ) -> KpEventBooking:
        try:
            statement = select(KpEventBookingService).where(
                col(KpEventBookingService.booking_id) == booking.id,
                col(KpEventBookingService.service_id).in_(list(quantities)),
            )
            result = await self.session.execute(statement)
            existing_by_service_id = {
                booking_service.service_id: booking_service
                for booking_service in result.scalars().all()
            }

            for service_id, quantity in quantities.items():
                booking_service = existing_by_service_id.get(service_id)
                if quantity == 0:
                    if booking_service is not None:
                        await self.session.delete(booking_service)
                    continue
                if booking_service is None:
                    booking_service = KpEventBookingService(
                        booking_id=booking.id,
                        service_id=service_id,
                        quantity=quantity,
                        included_quantity=0,
                    )
                else:
                    booking_service.quantity = quantity

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

    async def apply_zone_inclusions(
        self, booking: KpEventBooking, zone: KpEventBoothZone
    ) -> KpEventBooking:
        try:
            included_quantities = {
                included_service.service_id: included_service.included_quantity
                for included_service in zone.included_services
            }
            statement = select(KpEventBookingService).where(
                col(KpEventBookingService.booking_id) == booking.id
            )
            result = await self.session.execute(statement)
            booking_services = {
                booking_service.service_id: booking_service
                for booking_service in result.scalars().all()
            }

            for service_id, included_quantity in included_quantities.items():
                booking_service = booking_services.get(service_id)
                if booking_service is None:
                    booking_service = KpEventBookingService(
                        booking_id=booking.id,
                        service_id=service_id,
                        quantity=included_quantity,
                    )
                    booking_services[service_id] = booking_service
                booking_service.included_quantity = included_quantity
                booking_service.quantity = max(
                    booking_service.quantity, included_quantity
                )

            for service_id, booking_service in booking_services.items():
                if service_id not in included_quantities:
                    booking_service.included_quantity = 0
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

    async def add_booking_services(
        self,
        booking: KpEventBooking,
        services: Sequence[BookingServiceInput],
        after_confirmation: bool = False,
    ) -> KpEventBooking:
        try:
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
                if after_confirmation:
                    booking_service.added_after_confirmation += item.quantity

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
                selectinload(
                    rel(KpEventBookingUpgradeWaitlist.target_booth_zone)
                ).selectinload(rel(KpEventBoothZone.included_services)),
                selectinload(
                    rel(KpEventBookingUpgradeWaitlist.target_booth_zone)
                ).selectinload(rel(KpEventBoothZone.layout_stored_file)),
                selectinload(rel(KpEventBookingUpgradeWaitlist.booking)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_waitlist_entries_for_zone(
        self, booth_zone_id: UUID
    ) -> Sequence[KpEventBookingUpgradeWaitlist]:
        statement = (
            select(KpEventBookingUpgradeWaitlist)
            .where(
                col(KpEventBookingUpgradeWaitlist.target_booth_zone_id) == booth_zone_id
            )
            .order_by(
                col(KpEventBookingUpgradeWaitlist.priority_rank).asc().nulls_last(),
                col(KpEventBookingUpgradeWaitlist.created_at).asc(),
            )
            .options(selectinload(rel(KpEventBookingUpgradeWaitlist.booking)))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def delete_waitlist_entry(self, entry: KpEventBookingUpgradeWaitlist) -> None:
        try:
            await self.session.delete(entry)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

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
            removed_entries = {
                entry.target_booth_zone_id: entry for entry in result.scalars().all()
            }

            for priority_rank, target_booth_zone_id in enumerate(
                target_booth_zone_ids, start=1
            ):
                entry = removed_entries.pop(
                    target_booth_zone_id, None
                ) or KpEventBookingUpgradeWaitlist(
                    booking_id=booking.id,
                    target_booth_zone_id=target_booth_zone_id,
                )
                entry.priority_rank = priority_rank
                self._validate_model(
                    entry,
                    exclude={"booking", "target_booth_zone"},
                )
                self.session.add(entry)

            for entry in removed_entries.values():
                await self.session.delete(entry)

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
            .options(*_booth_zone_options())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_booth_zone_by_id(
        self, booth_zone_id: UUID
    ) -> Optional[KpEventBoothZone]:
        statement = (
            select(KpEventBoothZone)
            .where(col(KpEventBoothZone.id) == booth_zone_id)
            .options(*_booth_zone_options())
            .execution_options(populate_existing=True)
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
            .options(*_booth_zone_options())
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_booth_zone_by_color(
        self, event_id: UUID, color: str
    ) -> Optional[KpEventBoothZone]:
        statement = (
            select(KpEventBoothZone)
            .where(
                col(KpEventBoothZone.event_id) == event_id,
                col(KpEventBoothZone.color) == color,
            )
            .options(*_booth_zone_options())
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_services(
        self, event_id: UUID, category: KpServiceCategory | None = None
    ) -> Sequence[KpEventService]:
        statement = (
            select(KpEventService)
            .where(col(KpEventService.event_id) == event_id)
            .order_by(col(KpEventService.order).asc(), col(KpEventService.name).asc())
            .options(
                selectinload(rel(KpEventService.requirements)),
                selectinload(rel(KpEventService.image_stored_file)),
            )
        )
        if category is not None:
            statement = statement.where(col(KpEventService.category) == category)
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
            .execution_options(populate_existing=True)
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

    async def max_included_quantity(self, service_id: UUID) -> int:
        statement = select(
            func.coalesce(
                func.max(col(KpEventBoothZoneServiceLink.included_quantity)), 0
            )
        ).where(col(KpEventBoothZoneServiceLink.service_id) == service_id)
        result = await self.session.execute(statement)
        return result.scalar_one()

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
                selectinload(rel(KpEventBookingService.booking)).selectinload(
                    rel(KpEventBooking.event)
                ),
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
            await self.lock_model_by_id(KpEvent, event_id)
            background = await self.get_nametag_background(event_id)
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
                KpCompanyProfile,
                col(KpCompanyProfile.logo_stored_file_id) == col(StoredFile.id),
            )
            .outerjoin(
                KpVenueLayout,
                col(KpVenueLayout.background_stored_file_id) == col(StoredFile.id),
            )
            .outerjoin(
                KpEventBoothZone,
                col(KpEventBoothZone.layout_stored_file_id) == col(StoredFile.id),
            )
            .where(
                and_(
                    col(KpEventBookingServiceFileLink.id).is_(None),
                    col(KpEventNametagBackground.id).is_(None),
                    col(KpEventService.id).is_(None),
                    col(KpCompanyProfile.id).is_(None),
                    col(KpVenueLayout.id).is_(None),
                    col(KpEventBoothZone.id).is_(None),
                    col(StoredFile.updated_at) < cutoff,
                )
            )
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def replace_name_tags(
        self, booking: KpEventBooking, name_tags: Sequence[NameTagInput]
    ) -> Sequence[NameTag]:
        try:
            await self.hard_delete_where(NameTag, col(NameTag.booking_id) == booking.id)
            for name_tag_input in name_tags:
                name_tag = NameTag(booking_id=booking.id, **name_tag_input.model_dump())
                self._validate_model(name_tag, exclude={"booking"})
                self.session.add(name_tag)
            await self.session.commit()
            return await self.list_name_tags_for_booking(booking.id)
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
