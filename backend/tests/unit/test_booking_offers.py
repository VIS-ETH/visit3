from datetime import date, datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.kp_event import KpBookingStatus, KpEvent, KpEventBooking
from app.services.booking_offers import process_booking_offers

NOW = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
DEADLINE = date(2026, 10, 5)


def utc(month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=timezone.utc)


def make_offer(
    *,
    made_on: date = date(2026, 9, 20),
    week_sent: bool = False,
    day_sent: bool = False,
) -> KpEventBooking:
    event = KpEvent(
        id=uuid4(),
        name="Kontaktparty",
        registration_open=date(2026, 9, 1),
        registration_end=date(2026, 9, 30),
        finalization_deadline=date(2026, 10, 10),
        nametags_deadline=date(2026, 10, 12),
        event_date=date(2026, 10, 20),
    )
    booking = KpEventBooking(
        id=uuid4(),
        event_id=event.id,
        company_id=uuid4(),
        booth_zone_id=uuid4(),
        status=KpBookingStatus.OFFERED,
        offer_deadline=DEADLINE,
        offer_made_on=made_on,
        offer_week_reminder_sent_at=NOW if week_sent else None,
        offer_day_reminder_sent_at=NOW if day_sent else None,
    )
    booking.event = event
    return booking


def repository_with(offers: list[KpEventBooking]) -> AsyncMock:
    kp_repository = AsyncMock()
    kp_repository.list_pending_offers.return_value = offers
    kp_repository.update_booking.side_effect = lambda booking, _: booking
    kp_repository.lock_model_by_id.return_value = None
    return kp_repository


async def run(freeze_now, instant: datetime, offer: KpEventBooking):
    freeze_now(instant)
    kp_repository = repository_with([offer])
    notifier = AsyncMock()
    await process_booking_offers(kp_repository, notifier, NOW)
    return kp_repository, notifier


def updates(kp_repository: AsyncMock) -> list[dict[str, object]]:
    return [
        call.args[1].model_dump(exclude_unset=True)
        for call in kp_repository.update_booking.await_args_list
    ]


@pytest.mark.parametrize(
    ("instant", "expired"),
    [(utc(10, 5, 21, 59), False), (utc(10, 5, 22, 0), True)],
)
async def test_an_offer_expires_after_its_zurich_deadline_day(
    freeze_now, instant, expired
):
    kp_repository, _ = await run(freeze_now, instant, make_offer(day_sent=True))

    assert (
        {"status": KpBookingStatus.EXPIRED, "status_changed_at": NOW}
        in updates(kp_repository)
    ) is expired


async def test_the_week_reminder_goes_out_seven_days_before(freeze_now):
    kp_repository, notifier = await run(freeze_now, utc(9, 28, 10, 0), make_offer())

    notifier.booking_offer_week_reminder.assert_awaited_once()
    notifier.booking_offer_day_reminder.assert_not_awaited()
    assert updates(kp_repository) == [{"offer_week_reminder_sent_at": NOW}]


async def test_no_reminder_goes_out_eight_days_before(freeze_now):
    kp_repository, notifier = await run(freeze_now, utc(9, 27, 21, 59), make_offer())

    notifier.booking_offer_week_reminder.assert_not_awaited()
    assert updates(kp_repository) == []


async def test_the_day_reminder_goes_out_the_day_before(freeze_now):
    kp_repository, notifier = await run(
        freeze_now, utc(10, 3, 22, 30), make_offer(week_sent=True)
    )

    notifier.booking_offer_day_reminder.assert_awaited_once()
    notifier.booking_offer_week_reminder.assert_not_awaited()
    assert updates(kp_repository) == [{"offer_day_reminder_sent_at": NOW}]


async def test_a_sent_reminder_is_not_sent_again(freeze_now):
    kp_repository, notifier = await run(
        freeze_now, utc(9, 28, 10, 0), make_offer(week_sent=True)
    )

    notifier.booking_offer_week_reminder.assert_not_awaited()
    notifier.booking_offer_day_reminder.assert_not_awaited()
    assert updates(kp_repository) == []


async def test_a_late_week_reminder_is_skipped_once_the_day_reminder_is_due(
    freeze_now,
):
    kp_repository, notifier = await run(freeze_now, utc(10, 4, 10, 0), make_offer())

    notifier.booking_offer_week_reminder.assert_not_awaited()
    notifier.booking_offer_day_reminder.assert_awaited_once()


async def test_an_offer_made_with_only_a_week_left_gets_no_week_reminder(
    freeze_now,
):
    kp_repository, notifier = await run(
        freeze_now, utc(9, 28, 10, 0), make_offer(made_on=date(2026, 9, 28))
    )

    notifier.booking_offer_week_reminder.assert_not_awaited()
    assert updates(kp_repository) == []


async def test_an_offer_made_the_day_before_gets_no_day_reminder(freeze_now):
    kp_repository, notifier = await run(
        freeze_now, utc(10, 4, 10, 0), make_offer(made_on=date(2026, 10, 4))
    )

    notifier.booking_offer_day_reminder.assert_not_awaited()
    assert updates(kp_repository) == []
