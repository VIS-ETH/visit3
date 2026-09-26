from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.maintenance import DAILY, create_scheduler, remind_incomplete_bookings
from app.models.company import Company
from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
)
from app.services.booking_reminders import send_incomplete_booking_reminders
from tests.unit.conftest import complete_company_profile, complete_company_snapshot

FAKE_NOW = datetime(2026, 5, 4, 9, 30, tzinfo=timezone.utc)
REMINDER_DAYS = 3


def make_event(*, reminder_days: int = REMINDER_DAYS, deadline_in_days: int) -> KpEvent:
    deadline = date.today() + timedelta(days=deadline_in_days)
    return KpEvent(
        id=uuid4(),
        name="Kontaktparty",
        registration_open=deadline - timedelta(days=30),
        registration_end=deadline - timedelta(days=20),
        finalization_deadline=deadline,
        nametags_deadline=deadline + timedelta(days=1),
        event_date=deadline + timedelta(days=20),
        finalization_reminder_days=reminder_days,
    )


def make_booking(event: KpEvent, *, complete: bool) -> KpEventBooking:
    booking = KpEventBooking(
        id=uuid4(),
        event_id=event.id,
        company_id=uuid4(),
        booth_zone_id=uuid4(),
        status=KpBookingStatus.REGISTERED,
    )
    booking.event = event
    booking.services = []
    company = Company(id=booking.company_id, name="Acme AG")
    if complete:
        company.kp_profile = complete_company_profile(company.id)
        booking.company_details = complete_company_snapshot(booking.id)
    booking.company = company
    return booking


def repository_with(bookings: list[KpEventBooking]) -> AsyncMock:
    kp_repository = AsyncMock()
    kp_repository.list_registered_bookings_awaiting_reminder.return_value = bookings
    kp_repository.update_booking.side_effect = lambda booking, _: booking
    return kp_repository


async def test_the_job_asks_for_bookings_due_today():
    kp_repository = repository_with([])

    await send_incomplete_booking_reminders(kp_repository, AsyncMock(), FAKE_NOW)

    kp_repository.list_registered_bookings_awaiting_reminder.assert_awaited_once_with(
        date.today()
    )


async def test_incomplete_bookings_are_reminded_on_the_reminder_date():
    booking = make_booking(make_event(deadline_in_days=REMINDER_DAYS), complete=False)
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await send_incomplete_booking_reminders(kp_repository, notifier, FAKE_NOW)

    update = kp_repository.update_booking.await_args.args[1]
    assert update.reminder_sent_at == FAKE_NOW
    notifier.booking_incomplete_reminder.assert_awaited_once_with(booking)


async def test_nothing_happens_before_the_reminder_date():
    booking = make_booking(
        make_event(deadline_in_days=REMINDER_DAYS + 1), complete=False
    )
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await send_incomplete_booking_reminders(kp_repository, notifier, FAKE_NOW)

    kp_repository.update_booking.assert_not_awaited()
    notifier.booking_incomplete_reminder.assert_not_awaited()


async def test_a_missed_reminder_day_is_caught_up():
    booking = make_booking(
        make_event(deadline_in_days=REMINDER_DAYS - 1), complete=False
    )
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await send_incomplete_booking_reminders(
        kp_repository, notifier, FAKE_NOW + timedelta(days=1)
    )

    notifier.booking_incomplete_reminder.assert_awaited_once_with(booking)


async def test_a_missing_description_is_reminded():
    booking = make_booking(make_event(deadline_in_days=REMINDER_DAYS), complete=True)
    booking.company_details = complete_company_snapshot(booking.id, description="")
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await send_incomplete_booking_reminders(kp_repository, notifier, FAKE_NOW)

    notifier.booking_incomplete_reminder.assert_awaited_once_with(booking)


async def test_a_missing_general_email_is_reminded():
    booking = make_booking(make_event(deadline_in_days=REMINDER_DAYS), complete=True)
    booking.company_details = complete_company_snapshot(booking.id, general_email=None)
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await send_incomplete_booking_reminders(kp_repository, notifier, FAKE_NOW)

    notifier.booking_incomplete_reminder.assert_awaited_once_with(booking)


async def test_complete_bookings_are_not_reminded():
    booking = make_booking(make_event(deadline_in_days=REMINDER_DAYS), complete=True)
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await send_incomplete_booking_reminders(kp_repository, notifier, FAKE_NOW)

    kp_repository.update_booking.assert_not_awaited()
    notifier.booking_incomplete_reminder.assert_not_awaited()


async def test_a_reminded_booking_is_never_offered_again():
    event = make_event(deadline_in_days=REMINDER_DAYS)
    booking = make_booking(event, complete=False)
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await send_incomplete_booking_reminders(kp_repository, notifier, FAKE_NOW)
    booking.reminder_sent_at = FAKE_NOW
    kp_repository.list_registered_bookings_awaiting_reminder.return_value = []
    await send_incomplete_booking_reminders(
        kp_repository, notifier, FAKE_NOW + timedelta(hours=1)
    )

    notifier.booking_incomplete_reminder.assert_awaited_once()


def test_the_reminder_job_runs_daily():
    scheduler = create_scheduler()

    assert (remind_incomplete_bookings, DAILY) in scheduler._tasks
