from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.models.kp_event import KpBookingStatus, KpEvent, KpEventBooking


def make_event() -> KpEvent:
    return KpEvent(
        name="Kontaktparty",
        registration_open=date(2026, 9, 28),
        registration_end=date(2026, 10, 5),
        finalization_deadline=date(2026, 10, 10),
        nametags_deadline=date(2026, 10, 12),
        event_date=date(2026, 10, 20),
    )


def utc(month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        (utc(9, 27, 21, 59), False),
        (utc(9, 27, 22, 0), True),
        (utc(9, 27, 22, 37), True),
        (utc(10, 5, 21, 59), True),
        (utc(10, 5, 22, 0), False),
    ],
)
def test_registration_is_open_on_zurich_calendar_days(freeze_now, instant, expected):
    freeze_now(instant)

    assert make_event().is_registration_open() is expected


@pytest.mark.parametrize(
    ("instant", "expected"),
    [(utc(10, 10, 21, 59), False), (utc(10, 10, 22, 0), True)],
)
def test_finalization_deadline_passes_after_the_zurich_day(
    freeze_now, instant, expected
):
    freeze_now(instant)

    assert make_event().is_finalization_deadline_passed() is expected


@pytest.mark.parametrize(
    ("instant", "expected"),
    [(utc(10, 12, 21, 59), False), (utc(10, 12, 22, 0), True)],
)
def test_nametags_deadline_passes_after_the_zurich_day(freeze_now, instant, expected):
    freeze_now(instant)

    assert make_event().is_nametags_deadline_passed() is expected


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        (utc(10, 4, 21, 59), True),
        (utc(10, 4, 22, 30), True),
        (utc(10, 5, 21, 59), True),
        (utc(10, 5, 22, 0), False),
    ],
)
def test_an_offer_stays_open_through_its_zurich_deadline(freeze_now, instant, expected):
    freeze_now(instant)
    booking = KpEventBooking(
        event_id=uuid4(),
        company_id=uuid4(),
        booth_zone_id=uuid4(),
        status=KpBookingStatus.OFFERED,
        offer_deadline=date(2026, 10, 5),
    )

    assert booking.is_offer_open() is expected


def test_a_registered_booking_is_no_open_offer():
    booking = KpEventBooking(
        event_id=uuid4(),
        company_id=uuid4(),
        booth_zone_id=uuid4(),
        offer_deadline=date(2099, 10, 5),
    )

    assert booking.is_offer_open() is False
