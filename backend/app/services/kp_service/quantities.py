from collections.abc import Mapping, Sequence
from uuid import UUID

from app.core.exceptions import (
    KpServiceNotFound,
    KpServiceQuantityInvalid,
    KpServicesExcluded,
    KpServiceUnavailable,
)
from app.models.kp_event import (
    UNLIMITED_TOTAL_QUANTITY,
    KpEventBooking,
    KpEventBoothZone,
)
from app.schemas.kp import BookingServiceInput, StaffBookingServiceInput
from app.services.kp_service.base import KpServiceBase
from app.services.zone_switch_stock import service_exceeding_stock


def zone_included_quantities(zone: KpEventBoothZone) -> dict[UUID, int]:
    return {
        included_service.service_id: included_service.included_quantity
        for included_service in zone.included_services
    }


def booked_quantities(booking: KpEventBooking) -> dict[UUID, int]:
    return {
        booking_service.service_id: booking_service.quantity
        for booking_service in booking.services
    }


def requested_quantities(services: Sequence[BookingServiceInput]) -> dict[UUID, int]:
    quantities: dict[UUID, int] = {}
    for service in services:
        quantities[service.service_id] = (
            quantities.get(service.service_id, 0) + service.quantity
        )
    return quantities


def stored_quantities(
    quantities: Mapping[UUID, int], included_quantities: Mapping[UUID, int]
) -> dict[UUID, int]:
    return {
        service_id: max(
            quantities.get(service_id, 0), included_quantities.get(service_id, 0)
        )
        for service_id in quantities.keys() | included_quantities.keys()
    }


class ServiceQuantitiesMixin(KpServiceBase):
    async def _validate_service_quantity(
        self,
        *,
        event_id: UUID,
        service_id: UUID,
        stored_quantity: int,
        existing_quantity: int,
        included_quantity: int,
        context: str,
    ) -> None:
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"{context}:service_not_found:{service_id}")
        if service.event_id != event_id:
            raise KpServiceUnavailable(f"{context}:service_unavailable:{service_id}")
        if stored_quantity <= existing_quantity:
            return
        if not service.is_active:
            raise KpServiceUnavailable(f"{context}:service_unavailable:{service_id}")
        if stored_quantity > service.max_quantity_per_booking:
            raise KpServiceQuantityInvalid(
                f"booking_service:service_max_per_booking:{service_id}:{stored_quantity}"
            )
        charged_quantity = max(stored_quantity - included_quantity, 0) - max(
            existing_quantity - included_quantity, 0
        )
        if (
            service.max_total_quantity != UNLIMITED_TOTAL_QUANTITY
            and charged_quantity > 0
        ):
            booked_quantity = (
                await self.kp_repository.count_active_charged_service_quantity(
                    service_id
                )
            )
            if booked_quantity + charged_quantity > service.max_total_quantity:
                raise KpServiceQuantityInvalid(
                    f"{context}:service_max_total:{service_id}:{charged_quantity}"
                )

    async def _validate_booking_services(
        self,
        event_id: UUID,
        services: Sequence[BookingServiceInput],
        existing_quantities: dict[UUID, int] | None = None,
        included_quantities: dict[UUID, int] | None = None,
    ) -> list[BookingServiceInput]:
        existing_quantities = existing_quantities or {}
        included_quantities = included_quantities or {}
        validated_services: list[BookingServiceInput] = []
        for service_id, quantity in requested_quantities(services).items():
            existing_quantity = existing_quantities.get(service_id, 0)
            included_quantity = included_quantities.get(service_id, 0)
            await self._validate_service_quantity(
                event_id=event_id,
                service_id=service_id,
                stored_quantity=max(existing_quantity + quantity, included_quantity),
                existing_quantity=existing_quantity,
                included_quantity=included_quantity,
                context="register_booking",
            )
            validated_services.append(
                BookingServiceInput(service_id=service_id, quantity=quantity)
            )
        return validated_services

    async def _validated_service_quantities(
        self, booking: KpEventBooking, services: Sequence[StaffBookingServiceInput]
    ) -> dict[UUID, int]:
        existing_quantities = booked_quantities(booking)
        included_quantities = {
            booking_service.service_id: booking_service.included_quantity
            for booking_service in booking.services
        }
        quantities: dict[UUID, int] = {}
        for item in services:
            included_quantity = included_quantities.get(item.service_id, 0)
            stored_quantity = max(item.quantity, included_quantity)
            await self._validate_service_quantity(
                event_id=booking.event_id,
                service_id=item.service_id,
                stored_quantity=stored_quantity,
                existing_quantity=existing_quantities.get(item.service_id, 0),
                included_quantity=included_quantity,
                context="update_booking",
            )
            quantities[item.service_id] = stored_quantity
        return quantities

    async def _with_package_inclusions(
        self, zone_quantities: Mapping[UUID, int], quantities: Mapping[UUID, int]
    ) -> dict[UUID, int]:
        included = dict(zone_quantities)
        package_quantities = await self.kp_repository.package_inclusion_quantities(
            quantities
        )
        for service_id, quantity in package_quantities.items():
            included[service_id] = included.get(service_id, 0) + quantity
        return included

    async def _ensure_services_combinable(
        self,
        quantities: Mapping[UUID, int],
        zone_quantities: Mapping[UUID, int],
        context: str,
    ) -> None:
        selected = {
            service_id
            for service_id, quantity in quantities.items()
            if quantity > zone_quantities.get(service_id, 0)
        }
        for exclusion in await self.kp_repository.list_service_exclusions(
            list(selected)
        ):
            if exclusion.excluded_service_id in selected:
                raise KpServicesExcluded(
                    f"{context}:{exclusion.service_id}:{exclusion.excluded_service_id}"
                )

    async def _ensure_combinable_after_update(
        self, booking: KpEventBooking, quantities: Mapping[UUID, int]
    ) -> None:
        totals = booked_quantities(booking)
        totals.update(quantities)
        zone_quantities = await self.kp_repository.zone_inclusion_portion(booking.id)
        included_quantities = await self._with_package_inclusions(
            zone_quantities, totals
        )
        await self._ensure_services_combinable(
            stored_quantities(totals, included_quantities),
            zone_quantities,
            "update_booking",
        )

    async def _ensure_zone_switch_stock(
        self, booking: KpEventBooking, zone: KpEventBoothZone, context: str
    ) -> None:
        service = await service_exceeding_stock(self.kp_repository, booking, zone)
        if service is not None:
            raise KpServiceQuantityInvalid(
                f"{context}:service_max_total:{service.id}:{zone.id}"
            )
