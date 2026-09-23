from datetime import date, datetime

from app.repositories.kp_repository import KpRepository
from app.schemas.kp import UpdateBookingInput
from app.services.booking_completeness import booking_completeness
from app.services.booking_notifier import BookingNotifier, notify_best_effort


async def send_incomplete_booking_reminders(
    kp_repository: KpRepository, notifier: BookingNotifier, now: datetime
) -> None:
    today = date.today()
    bookings = await kp_repository.list_registered_bookings_awaiting_reminder(today)
    for booking in bookings:
        if booking.event.finalization_reminder_date > today:
            continue
        if not booking_completeness(booking):
            continue
        reminded = await kp_repository.update_booking(
            booking, UpdateBookingInput(reminder_sent_at=now)
        )
        await notify_best_effort(notifier.booking_incomplete_reminder(reminded))
