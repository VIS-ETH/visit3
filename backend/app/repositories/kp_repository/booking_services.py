from collections.abc import Sequence
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.kp_event import KpEventBooking, KpEventBookingService
from app.repositories.base import rel
from app.repositories.kp_repository.inclusions import InclusionsMixin
from app.schemas.kp import BookingServiceInput


class BookingServicesMixin(InclusionsMixin):
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

    async def acknowledge_booking_additions(
        self, booking: KpEventBooking
    ) -> KpEventBooking:
        async with self.committing():
            for booking_service in booking.services:
                booking_service.added_after_confirmation = 0
                self.session.add(booking_service)
        return await self.get_booking_by_id(booking.id) or booking

    async def set_booking_service_quantities(
        self,
        booking: KpEventBooking,
        quantities: dict[UUID, int],
    ) -> KpEventBooking:
        async with self.committing():
            zone_quantities = await self.zone_inclusion_portion(booking.id)
            existing_by_service_id = await self._booking_services(
                booking.id, list(quantities)
            )

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

                self._validate_model(booking_service)
                self.session.add(booking_service)

            await self.session.flush()
            await self._sync_inclusions(booking.id, zone_quantities)
        return await self.get_booking_by_id(booking.id) or booking

    async def add_booking_services(
        self,
        booking: KpEventBooking,
        services: Sequence[BookingServiceInput],
        after_confirmation: bool = False,
    ) -> KpEventBooking:
        async with self.committing():
            zone_quantities = await self.zone_inclusion_portion(booking.id)
            existing_by_service_id = await self._booking_services(
                booking.id, [item.service_id for item in services]
            )

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

                self._validate_model(booking_service)
                self.session.add(booking_service)

            await self.session.flush()
            await self._sync_inclusions(booking.id, zone_quantities)
        return await self.get_booking_by_id(booking.id) or booking
