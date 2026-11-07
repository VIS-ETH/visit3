from uuid import UUID

from app.core.auth_context import require_staff_user
from app.core.exceptions import (
    KpBookingDeleteRequiresForce,
    KpBookingNotFound,
    KpBoothNumberTaken,
)
from app.models.kp_event import KpBookingStatus, KpEventBooking, KpEventBoothZone
from app.schemas.kp import (
    BookingSummaryResponse,
    BookingWithCompanyAndBoothZoneResponse,
    StaffUpdateBookingInput,
    UpdateBookingBoothNumberInput,
    UpdateBookingInput,
)
from app.services.booking_summary import booking_summary
from app.services.event_lookup import require_locked_event
from app.services.kp_service.quantities import ServiceQuantitiesMixin
from app.services.kp_service.responses import ResponsesMixin


class StaffBookingsMixin(ResponsesMixin, ServiceQuantitiesMixin):
    async def list_bookings_for_event(
        self, event_id: UUID
    ) -> list[BookingWithCompanyAndBoothZoneResponse]:
        require_staff_user(self.current_user)
        await self._get_event(event_id)
        bookings = await self.kp_repository.list_bookings_for_event(event_id)
        return [
            await self._build_staff_booking_response(booking) for booking in bookings
        ]

    async def get_bookings_summary(self, event_id: UUID) -> BookingSummaryResponse:
        require_staff_user(self.current_user)
        event = await self._get_event(event_id)
        return booking_summary(
            event,
            await self.kp_repository.list_booth_zones(event_id),
            await self.kp_repository.list_services(event_id),
            await self.kp_repository.list_bookings_for_event(event_id),
        )

    async def get_event_booking(
        self, event_id: UUID, booking_id: UUID
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        await self._get_event(event_id)
        booking = await self._get_booking(booking_id)
        if booking.event_id != event_id:
            raise KpBookingNotFound(f"booking:event_mismatch:{event_id}:{booking_id}")
        return await self._build_staff_booking_response(booking)

    async def _ensure_booth_number_free(
        self,
        booking: KpEventBooking,
        booth_zone_id: UUID,
        booth_nr: int | None,
        context: str,
    ) -> None:
        if booth_nr is None:
            return
        occupant = await self.kp_repository.get_active_booking_by_booth_number(
            booking.event_id, booth_zone_id, booth_nr
        )
        if occupant is not None and occupant.id != booking.id:
            raise KpBoothNumberTaken(f"{context}:taken:{booking.id}:{booth_nr}")

    async def update_booking_booth_number(
        self, booking_id: UUID, update_booking_input: UpdateBookingBoothNumberInput
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        booth_nr = update_booking_input.booth_nr
        await self._ensure_booth_number_free(
            booking, booking.booth_zone_id, booth_nr, "update_booking_booth_number"
        )
        updated = await self.kp_repository.update_booking(
            booking, UpdateBookingInput(booth_nr=booth_nr)
        )
        return await self._build_staff_booking_response(updated)

    async def _locked_target_booth_zone(
        self, booking: KpEventBooking, booth_zone_id: UUID
    ) -> KpEventBoothZone:
        await self._get_event_booth_zone(
            booth_zone_id, booking.event_id, "update_booking"
        )
        locked_zone = await self._lock_zone_until_booking_is_inserted(booth_zone_id)
        await self._ensure_zone_not_full(
            booking.event_id, locked_zone, "update_booking"
        )
        return locked_zone

    async def update_booking(
        self, booking_id: UUID, staff_update_booking_input: StaffUpdateBookingInput
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        await require_locked_event(
            self.kp_repository,
            booking.event_id,
            f"update_booking:event_not_found:{booking.event_id}",
        )
        updates = staff_update_booking_input.model_dump(exclude_unset=True)
        target_zone_id = staff_update_booking_input.booth_zone_id
        moving = target_zone_id is not None and target_zone_id != booking.booth_zone_id
        target_zone = (
            await self._locked_target_booth_zone(booking, target_zone_id)
            if moving and target_zone_id is not None
            else None
        )
        booking = await self._get_booking(booking_id, lock=True)
        left_booth_zone_id = booking.booth_zone_id

        if target_zone is not None:
            await self._ensure_zone_switch_stock(booking, target_zone, "update_booking")
        changes: dict[str, object] = {}
        if "booth_nr" in updates:
            await self._ensure_booth_number_free(
                booking,
                target_zone.id if target_zone is not None else booking.booth_zone_id,
                staff_update_booking_input.booth_nr,
                "update_booking",
            )
            changes["booth_nr"] = staff_update_booking_input.booth_nr
        if "status_note" in updates:
            changes["status_note"] = staff_update_booking_input.status_note
        quantities: dict[UUID, int] = {}
        if staff_update_booking_input.services is not None:
            quantities = await self._validated_service_quantities(
                booking, staff_update_booking_input.services
            )
            await self._ensure_combinable_after_update(booking, quantities)

        updated = booking
        if target_zone is not None:
            updated = await self.kp_repository.move_booking_to_zone(
                updated, target_zone, clear_whole_waitlist=False
            )
        if changes:
            updated = await self.kp_repository.update_booking(
                updated, UpdateBookingInput.model_validate(changes)
            )
        if quantities:
            updated = await self.kp_repository.set_booking_service_quantities(
                updated, quantities
            )
        if target_zone is not None:
            await self._promote_waitlist(updated.event_id, left_booth_zone_id)
        return await self._build_staff_booking_response(updated)

    async def delete_booking(self, booking_id: UUID, force: bool = False) -> None:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        if booking.status == KpBookingStatus.CONFIRMED and not force:
            raise KpBookingDeleteRequiresForce(
                f"delete_booking:confirmed:{booking_id}:{booking.status}"
            )
        event_id = booking.event_id
        booth_zone_id = booking.booth_zone_id
        await self.kp_repository.delete_booking(booking)
        await self._promote_waitlist(event_id, booth_zone_id)
