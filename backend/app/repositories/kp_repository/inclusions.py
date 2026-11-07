from collections.abc import Mapping, Sequence
from uuid import UUID

from sqlalchemy import func
from sqlmodel import col, select

from app.models.kp_event import (
    KpEventBookingService,
    KpEventBoothZoneServiceLink,
    KpEventServiceExclusion,
    KpEventServiceInclusion,
)
from app.repositories.kp_repository.base import KpRepositoryBase


class InclusionsMixin(KpRepositoryBase):
    async def max_included_quantity(self, service_id: UUID) -> int:
        zone_statement = select(
            func.coalesce(
                func.max(col(KpEventBoothZoneServiceLink.included_quantity)), 0
            )
        ).where(col(KpEventBoothZoneServiceLink.service_id) == service_id)
        package_statement = select(
            func.coalesce(func.max(col(KpEventServiceInclusion.included_quantity)), 0)
        ).where(col(KpEventServiceInclusion.included_service_id) == service_id)
        zone_quantity = (await self.session.execute(zone_statement)).scalar_one()
        package_quantity = (await self.session.execute(package_statement)).scalar_one()
        return max(zone_quantity, package_quantity)

    async def list_service_inclusions(
        self, service_ids: Sequence[UUID]
    ) -> Sequence[KpEventServiceInclusion]:
        if not service_ids:
            return []
        statement = select(KpEventServiceInclusion).where(
            col(KpEventServiceInclusion.service_id).in_(list(service_ids))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_containing_services(
        self, service_id: UUID
    ) -> Sequence[KpEventServiceInclusion]:
        statement = select(KpEventServiceInclusion).where(
            col(KpEventServiceInclusion.included_service_id) == service_id
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_service_exclusions(
        self, service_ids: Sequence[UUID]
    ) -> Sequence[KpEventServiceExclusion]:
        if not service_ids:
            return []
        statement = select(KpEventServiceExclusion).where(
            col(KpEventServiceExclusion.service_id).in_(list(service_ids))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def package_inclusion_quantities(
        self, quantities: Mapping[UUID, int]
    ) -> dict[UUID, int]:
        booked_ids = [
            service_id for service_id, quantity in quantities.items() if quantity > 0
        ]
        included: dict[UUID, int] = {}
        for inclusion in await self.list_service_inclusions(booked_ids):
            included[inclusion.included_service_id] = (
                included.get(inclusion.included_service_id, 0)
                + inclusion.included_quantity
            )
        return included

    async def _booking_services(
        self, booking_id: UUID, service_ids: Sequence[UUID] | None = None
    ) -> dict[UUID, KpEventBookingService]:
        statement = select(KpEventBookingService).where(
            col(KpEventBookingService.booking_id) == booking_id
        )
        if service_ids is not None:
            if not service_ids:
                return {}
            statement = statement.where(
                col(KpEventBookingService.service_id).in_(list(service_ids))
            )
        result = await self.session.execute(statement)
        return {
            booking_service.service_id: booking_service
            for booking_service in result.scalars().all()
        }

    async def zone_inclusion_portion(self, booking_id: UUID) -> dict[UUID, int]:
        booking_services = await self._booking_services(booking_id)
        package_quantities = await self.package_inclusion_quantities(
            {
                service_id: booking_service.quantity
                for service_id, booking_service in booking_services.items()
            }
        )
        portion = {
            service_id: booking_service.included_quantity
            - package_quantities.get(service_id, 0)
            for service_id, booking_service in booking_services.items()
        }
        return {
            service_id: quantity
            for service_id, quantity in portion.items()
            if quantity > 0
        }

    async def _sync_inclusions(
        self, booking_id: UUID, zone_quantities: Mapping[UUID, int]
    ) -> None:
        booking_services = await self._booking_services(booking_id)
        included_quantities = dict(zone_quantities)
        package_quantities = await self.package_inclusion_quantities(
            {
                service_id: booking_service.quantity
                for service_id, booking_service in booking_services.items()
            }
        )
        for service_id, quantity in package_quantities.items():
            included_quantities[service_id] = (
                included_quantities.get(service_id, 0) + quantity
            )

        for service_id, included_quantity in included_quantities.items():
            booking_service = booking_services.get(service_id)
            if booking_service is None:
                booking_service = KpEventBookingService(
                    booking_id=booking_id,
                    service_id=service_id,
                    quantity=included_quantity,
                )
                booking_services[service_id] = booking_service
            booking_service.included_quantity = included_quantity
            booking_service.quantity = max(booking_service.quantity, included_quantity)

        for service_id, booking_service in booking_services.items():
            if service_id not in included_quantities:
                booking_service.included_quantity = 0
            self._validate_model(booking_service)
            self.session.add(booking_service)
