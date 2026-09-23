from datetime import datetime

from app.models.kp_event import KpBookingStatus
from app.repositories.kp_repository import KpRepository
from app.schemas.kp import UpdateBookingInput
from app.services.booking_completeness import booking_completeness
from app.services.booking_notifier import BookingNotifier, notify_best_effort


async def auto_finalize_bookings(
    kp_repository: KpRepository, notifier: BookingNotifier, now: datetime
) -> None:
    bookings = await kp_repository.list_registered_bookings_past_finalization_deadline(
        now.date()
    )
    for booking in bookings:
        missing_items = booking_completeness(booking)
        if not missing_items:
            finalized = await kp_repository.update_booking(
                booking,
                UpdateBookingInput(
                    status=KpBookingStatus.FINALIZED,
                    status_changed_at=now,
                    finalized_at=now,
                ),
            )
            await notify_best_effort(notifier.booking_finalized(finalized))
        elif booking.auto_finalize_blocked_at is None:
            blocked = await kp_repository.update_booking(
                booking, UpdateBookingInput(auto_finalize_blocked_at=now)
            )
            await notify_best_effort(
                notifier.booking_incomplete_at_deadline(blocked, missing_items)
            )
