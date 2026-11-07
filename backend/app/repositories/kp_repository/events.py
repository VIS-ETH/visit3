from collections.abc import Sequence
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.kp_event import (
    KpEvent,
    KpEventBoothZone,
    KpEventBoothZoneServiceLink,
    KpEventRegistrationException,
    KpEventService,
    KpEventServiceExclusion,
    KpEventServiceInclusion,
    KpEventServiceRequirement,
)
from app.models.venue import KpVenueBooth, KpVenueLayout, KpVenueZoneShape
from app.repositories.base import rel
from app.repositories.kp_repository.base import KpRepositoryBase
from app.schemas.kp import CloneKpInput, CreateKpInput, UpdateKpInput, kp_event_columns

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

VENUE_LAYOUT_CLONE_FIELDS = (
    "name",
    "order",
    "width",
    "height",
    "is_active",
    "floor_plan",
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


class EventsMixin(KpRepositoryBase):
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
        async with self.committing():
            event = KpEvent(**kp_event_columns(create_kp_input.model_dump()))
            self._validate_model(event)
            self.session.add(event)
        await self.session.refresh(event)
        return event

    async def update_kp(
        self, event: KpEvent, update_kp_input: UpdateKpInput
    ) -> KpEvent:
        async with self.committing():
            event.sqlmodel_update(
                kp_event_columns(update_kp_input.model_dump(exclude_unset=True))
            )
            self._validate_model(event)
            self.session.add(event)
        await self.session.refresh(event)
        return event

    async def clone_kp(
        self, event_id: UUID, clone_kp_input: CloneKpInput
    ) -> Optional[KpEvent]:
        statement = (
            select(KpEvent)
            .where(col(KpEvent.id) == event_id)
            .options(
                selectinload(rel(KpEvent.services)).selectinload(
                    rel(KpEventService.requirements)
                ),
                selectinload(rel(KpEvent.services)).selectinload(
                    rel(KpEventService.included_services)
                ),
                selectinload(rel(KpEvent.services)).selectinload(
                    rel(KpEventService.excluded_services)
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

        async with self.committing():
            cloned_event = KpEvent(
                **kp_event_columns(clone_kp_input.model_dump()),
                booklet_background_stored_file_id=(
                    source_event.booklet_background_stored_file_id
                ),
                banner_id=source_event.banner_id,
            )
            self._validate_model(cloned_event)
            self.session.add(cloned_event)

            service_id_map = self._clone_services(source_event, cloned_event.id)
            booth_zone_id_map = self._clone_booth_zones(
                source_event, cloned_event.id, service_id_map
            )
            await self._clone_venue_layouts(
                source_event.id, cloned_event.id, booth_zone_id_map
            )
        await self.session.refresh(cloned_event)
        return cloned_event

    def _clone_services(
        self, source_event: KpEvent, cloned_event_id: UUID
    ) -> dict[UUID, UUID]:
        service_id_map: dict[UUID, UUID] = {}
        for service in source_event.services:
            cloned_service = self._clone_model(
                KpEventService,
                service,
                SERVICE_CLONE_FIELDS,
                event_id=cloned_event_id,
            )
            service_id_map[service.id] = cloned_service.id

            for requirement in service.requirements:
                self._clone_model(
                    KpEventServiceRequirement,
                    requirement,
                    SERVICE_REQUIREMENT_CLONE_FIELDS,
                    service_id=cloned_service.id,
                )

        for service in source_event.services:
            for inclusion in service.included_services:
                cloned_included_id = service_id_map.get(inclusion.included_service_id)
                if cloned_included_id is None:
                    continue
                self.session.add(
                    KpEventServiceInclusion(
                        service_id=service_id_map[service.id],
                        included_service_id=cloned_included_id,
                        included_quantity=inclusion.included_quantity,
                    )
                )
            for exclusion in service.excluded_services:
                cloned_excluded_id = service_id_map.get(exclusion.excluded_service_id)
                if cloned_excluded_id is None:
                    continue
                self.session.add(
                    KpEventServiceExclusion(
                        service_id=service_id_map[service.id],
                        excluded_service_id=cloned_excluded_id,
                    )
                )
        return service_id_map

    def _clone_booth_zones(
        self,
        source_event: KpEvent,
        cloned_event_id: UUID,
        service_id_map: dict[UUID, UUID],
    ) -> dict[UUID, UUID]:
        booth_zone_id_map: dict[UUID, UUID] = {}
        for booth_zone in source_event.booth_zones:
            cloned_booth_zone = self._clone_model(
                KpEventBoothZone,
                booth_zone,
                BOOTH_ZONE_CLONE_FIELDS,
                event_id=cloned_event_id,
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
        return booth_zone_id_map

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
        async with self.committing():
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
        await self.session.refresh(exception)
        return exception

    async def delete_registration_exception(
        self, exception: KpEventRegistrationException
    ) -> None:
        async with self.committing():
            await self.session.delete(exception)
