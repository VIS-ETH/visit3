from collections.abc import Sequence
from typing import Optional
from uuid import UUID

from sqlmodel import col, select

from app.models.kp_event import (
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventBoothZoneServiceLink,
)
from app.models.venue import KpVenueBooth, KpVenueZoneShape
from app.repositories.kp_repository.base import KpRepositoryBase, booth_zone_options
from app.schemas.kp import (
    CreateBoothZoneInput,
    IncludedServiceInput,
    UpdateBoothZoneInput,
)


class ZonesMixin(KpRepositoryBase):
    async def list_booth_zones(self, event_id: UUID) -> Sequence[KpEventBoothZone]:
        statement = (
            select(KpEventBoothZone)
            .where(col(KpEventBoothZone.event_id) == event_id)
            .order_by(
                col(KpEventBoothZone.order).asc(), col(KpEventBoothZone.name).asc()
            )
            .options(*booth_zone_options())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_booth_zone_by_id(
        self, booth_zone_id: UUID
    ) -> Optional[KpEventBoothZone]:
        statement = self._booth_zone_select().where(
            col(KpEventBoothZone.id) == booth_zone_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_booth_zone_by_name(
        self, event_id: UUID, name: str
    ) -> Optional[KpEventBoothZone]:
        statement = self._booth_zone_select().where(
            col(KpEventBoothZone.event_id) == event_id,
            col(KpEventBoothZone.name) == name,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_booth_zone_by_color(
        self, event_id: UUID, color: str
    ) -> Optional[KpEventBoothZone]:
        statement = self._booth_zone_select().where(
            col(KpEventBoothZone.event_id) == event_id,
            col(KpEventBoothZone.color) == color,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def lock_booth_zone(self, booth_zone_id: UUID) -> Optional[KpEventBoothZone]:
        statement = (
            self._booth_zone_select()
            .where(col(KpEventBoothZone.id) == booth_zone_id)
            .with_for_update(of=KpEventBoothZone)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def _reload_booth_zone(self, booth_zone_id: UUID) -> KpEventBoothZone:
        statement = self._booth_zone_select().where(
            col(KpEventBoothZone.id) == booth_zone_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def create_booth_zone(
        self, event_id: UUID, create_booth_zone_input: CreateBoothZoneInput
    ) -> KpEventBoothZone:
        async with self.committing():
            zone = KpEventBoothZone(
                **create_booth_zone_input.model_dump(exclude={"included_services"}),
                event_id=event_id,
            )
            self._validate_model(zone)
            self.session.add(zone)
            await self.session.flush()
            await self._replace_included_services(
                zone, create_booth_zone_input.included_services
            )
        return await self._reload_booth_zone(zone.id)

    async def update_booth_zone(
        self, zone: KpEventBoothZone, update_booth_zone_input: UpdateBoothZoneInput
    ) -> KpEventBoothZone:
        async with self.committing():
            zone.sqlmodel_update(
                update_booth_zone_input.model_dump(
                    exclude_unset=True, exclude={"included_services"}
                )
            )
            self._validate_model(zone)
            self.session.add(zone)
            if update_booth_zone_input.included_services is not None:
                await self._replace_included_services(
                    zone, update_booth_zone_input.included_services
                )
        return await self._reload_booth_zone(zone.id)

    async def reorder_booth_zones(
        self, event_id: UUID, zones: Sequence[KpEventBoothZone]
    ) -> Sequence[KpEventBoothZone]:
        async with self.committing():
            for position, zone in enumerate(zones):
                zone.order = position
                self.session.add(zone)
        return await self.list_booth_zones(event_id)

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
            self._validate_model(link)
            self.session.add(link)

        for link in removed.values():
            await self.session.delete(link)

    async def set_booth_zone_layout_stored_file_id(
        self, zone: KpEventBoothZone, stored_file_id: UUID | None
    ) -> KpEventBoothZone:
        async with self.committing():
            zone.layout_stored_file_id = stored_file_id
            self.session.add(zone)
        return await self._reload_booth_zone(zone.id)

    async def delete_booth_zone(self, zone: KpEventBoothZone) -> None:
        async with self.committing():
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
