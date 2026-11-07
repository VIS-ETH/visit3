from uuid import UUID

from app.core.auth_context import require_assigned_company_user, require_staff_user
from app.core.dates import utc_now
from app.core.exceptions import KpBookingStatusTransitionInvalid
from app.models.kp_event import KpBookingStatus, KpEventBooking
from app.schemas.kp import (
    BookingResponse,
    BookingWithCompanyAndBoothZoneResponse,
    RejectBookingInput,
    UpdateBookingInput,
    UpdateBookingStatusInput,
)
from app.services.booking_notifier import notify_best_effort
from app.services.kp_service.responses import ResponsesMixin

BookingTransitions = dict[KpBookingStatus, frozenset[KpBookingStatus]]

COMPANY_BOOKING_TRANSITIONS: BookingTransitions = {
    KpBookingStatus.OFFERED: frozenset({KpBookingStatus.CANCELLED}),
    KpBookingStatus.REGISTERED: frozenset({KpBookingStatus.CANCELLED}),
    KpBookingStatus.CONFIRMED: frozenset(),
    KpBookingStatus.CANCELLED: frozenset(),
    KpBookingStatus.REJECTED: frozenset(),
    KpBookingStatus.EXPIRED: frozenset(),
}

STAFF_BOOKING_TRANSITIONS: BookingTransitions = {
    KpBookingStatus.OFFERED: frozenset({KpBookingStatus.REJECTED}),
    KpBookingStatus.REGISTERED: frozenset(
        {KpBookingStatus.CONFIRMED, KpBookingStatus.REJECTED}
    ),
    KpBookingStatus.CONFIRMED: frozenset({KpBookingStatus.REGISTERED}),
    KpBookingStatus.CANCELLED: frozenset(),
    KpBookingStatus.REJECTED: frozenset(),
    KpBookingStatus.EXPIRED: frozenset(),
}


def ensure_booking_transition(
    transitions: BookingTransitions,
    booking: KpEventBooking,
    next_status: KpBookingStatus,
    context: str,
) -> None:
    if next_status not in transitions.get(booking.status, frozenset()):
        raise KpBookingStatusTransitionInvalid(
            f"{context}:{booking.id}:{booking.status}->{next_status}"
        )


class BookingStatusMixin(ResponsesMixin):
    async def update_my_booking_status(
        self, booking_id: UUID, update_booking_input: UpdateBookingStatusInput
    ) -> BookingResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "update_my_booking_status", lock=True
        )
        next_status = update_booking_input.status
        if booking.status == next_status:
            return await self._build_booking_response(booking)
        ensure_booking_transition(
            COMPANY_BOOKING_TRANSITIONS,
            booking,
            next_status,
            "update_my_booking_status",
        )
        updated = await self.kp_repository.update_booking(
            booking,
            UpdateBookingInput(status=next_status, status_changed_at=utc_now()),
        )
        await self._promote_waitlist(updated.event_id, updated.booth_zone_id)
        return await self._build_booking_response(updated)

    async def accept_booking(
        self, booking_id: UUID
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id, lock=True)
        if booking.status == KpBookingStatus.CONFIRMED:
            return await self._build_staff_booking_response(booking)
        ensure_booking_transition(
            STAFF_BOOKING_TRANSITIONS,
            booking,
            KpBookingStatus.CONFIRMED,
            "accept_booking",
        )
        changed_at = utc_now()
        acknowledged = await self.kp_repository.acknowledge_booking_additions(booking)
        updated = await self.kp_repository.update_booking(
            acknowledged,
            UpdateBookingInput(
                status=KpBookingStatus.CONFIRMED,
                status_changed_at=changed_at,
                confirmed_at=changed_at,
            ),
        )
        await notify_best_effort(self.notifier.booking_accepted(updated))
        return await self._build_staff_booking_response(updated)

    async def acknowledge_booking_additions(
        self, booking_id: UUID
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        updated = await self.kp_repository.acknowledge_booking_additions(booking)
        return await self._build_staff_booking_response(updated)

    async def undo_accept_booking(
        self, booking_id: UUID
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id, lock=True)
        ensure_booking_transition(
            STAFF_BOOKING_TRANSITIONS,
            booking,
            KpBookingStatus.REGISTERED,
            "undo_accept_booking",
        )
        updated = await self.kp_repository.update_booking(
            booking,
            UpdateBookingInput(
                status=KpBookingStatus.REGISTERED,
                status_changed_at=utc_now(),
                confirmed_at=None,
            ),
        )
        return await self._build_staff_booking_response(updated)

    async def reject_booking(
        self, booking_id: UUID, reject_booking_input: RejectBookingInput
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id, lock=True)
        ensure_booking_transition(
            STAFF_BOOKING_TRANSITIONS,
            booking,
            KpBookingStatus.REJECTED,
            "reject_booking",
        )
        updated = await self.kp_repository.update_booking(
            booking,
            UpdateBookingInput(
                status=KpBookingStatus.REJECTED,
                status_changed_at=utc_now(),
                rejection_reason=reject_booking_input.reason,
            ),
        )
        await self._promote_waitlist(updated.event_id, updated.booth_zone_id)
        await notify_best_effort(
            self.notifier.booking_rejected(updated, reject_booking_input.reason)
        )
        return await self._build_staff_booking_response(updated)
