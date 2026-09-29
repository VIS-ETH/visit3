from datetime import date, datetime

from app.core.dates import local_today
from app.models.kp_event import KpBookingStatus, KpEventBooking
from app.repositories.kp_repository import KpRepository
from app.schemas.kp import UpdateBookingInput
from app.services.booking_notifier import BookingNotifier, notify_best_effort
from app.services.waitlist_promotion import promote_waitlist

WEEK_REMINDER_DAYS = 7
DAY_REMINDER_DAYS = 1


def days_between(start: date | None, end: date) -> int:
    return (end - start).days if start is not None else 0


def week_reminder_due(booking: KpEventBooking, deadline: date, today: date) -> bool:
    return (
        booking.offer_week_reminder_sent_at is None
        and days_between(today, deadline) == WEEK_REMINDER_DAYS
        and days_between(booking.offer_made_on, deadline) > WEEK_REMINDER_DAYS
    )


def day_reminder_due(booking: KpEventBooking, deadline: date, today: date) -> bool:
    return (
        booking.offer_day_reminder_sent_at is None
        and days_between(today, deadline) == DAY_REMINDER_DAYS
        and days_between(booking.offer_made_on, deadline) > DAY_REMINDER_DAYS
    )


async def expire_offer(
    kp_repository: KpRepository,
    notifier: BookingNotifier,
    booking: KpEventBooking,
    now: datetime,
) -> None:
    expired = await kp_repository.update_booking(
        booking,
        UpdateBookingInput(status=KpBookingStatus.EXPIRED, status_changed_at=now),
    )
    await promote_waitlist(
        kp_repository, notifier, expired.event_id, expired.booth_zone_id
    )


async def remind_offer(
    kp_repository: KpRepository,
    notifier: BookingNotifier,
    booking: KpEventBooking,
    deadline: date,
    now: datetime,
) -> None:
    today = local_today()
    if week_reminder_due(booking, deadline, today):
        reminded = await kp_repository.update_booking(
            booking, UpdateBookingInput(offer_week_reminder_sent_at=now)
        )
        await notify_best_effort(
            notifier.booking_offer_week_reminder(reminded, deadline)
        )
    elif day_reminder_due(booking, deadline, today):
        reminded = await kp_repository.update_booking(
            booking, UpdateBookingInput(offer_day_reminder_sent_at=now)
        )
        await notify_best_effort(
            notifier.booking_offer_day_reminder(reminded, deadline)
        )


async def process_booking_offers(
    kp_repository: KpRepository, notifier: BookingNotifier, now: datetime
) -> None:
    for booking in await kp_repository.list_pending_offers():
        deadline = booking.offer_deadline
        if deadline is None:
            continue
        if not booking.is_offer_open():
            await expire_offer(kp_repository, notifier, booking, now)
            continue
        await remind_offer(kp_repository, notifier, booking, deadline, now)
