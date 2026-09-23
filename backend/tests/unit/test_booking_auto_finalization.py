from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from app.models.company import Company
from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
)
from app.services.booking_completeness import (
    BILLING_ADDRESS_MISSING,
    COMPANY_PROFILE_MISSING,
)
from app.services.booking_finalization import auto_finalize_bookings
from tests.unit.conftest import complete_company_profile, complete_company_snapshot

FAKE_NOW = datetime(2026, 5, 4, 9, 30, tzinfo=timezone.utc)


def make_event() -> KpEvent:
    deadline = FAKE_NOW.date() - timedelta(days=1)
    return KpEvent(
        id=uuid4(),
        name="Kontaktparty",
        registration_open=deadline - timedelta(days=20),
        registration_end=deadline - timedelta(days=10),
        finalization_deadline=deadline,
        nametags_deadline=deadline + timedelta(days=1),
        event_date=deadline + timedelta(days=20),
    )


def make_booking(
    *,
    complete: bool = True,
    auto_finalize_blocked_at: datetime | None = None,
) -> KpEventBooking:
    event = make_event()
    booking = KpEventBooking(
        id=uuid4(),
        event_id=event.id,
        company_id=uuid4(),
        booth_zone_id=uuid4(),
        status=KpBookingStatus.REGISTERED,
        auto_finalize_blocked_at=auto_finalize_blocked_at,
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
    kp_repository.list_registered_bookings_past_finalization_deadline.return_value = (
        bookings
    )
    kp_repository.update_booking.side_effect = lambda booking, _: booking
    return kp_repository


async def test_the_job_asks_for_bookings_due_at_the_given_clock():
    kp_repository = repository_with([])

    await auto_finalize_bookings(kp_repository, AsyncMock(), FAKE_NOW)

    kp_repository.list_registered_bookings_past_finalization_deadline.assert_awaited_once_with(
        date(2026, 5, 4)
    )


async def test_complete_bookings_are_finalized_with_the_fake_clock():
    booking = make_booking()
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await auto_finalize_bookings(kp_repository, notifier, FAKE_NOW)

    update = kp_repository.update_booking.await_args.args[1]
    assert update.status == KpBookingStatus.FINALIZED
    assert update.status_changed_at == FAKE_NOW
    assert update.finalized_at == FAKE_NOW
    notifier.booking_finalized.assert_awaited_once_with(booking)
    notifier.booking_incomplete_at_deadline.assert_not_awaited()


async def test_incomplete_bookings_stay_registered_and_are_marked_blocked():
    booking = make_booking(complete=False)
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await auto_finalize_bookings(kp_repository, notifier, FAKE_NOW)

    update = kp_repository.update_booking.await_args.args[1]
    assert update.status is None
    assert update.auto_finalize_blocked_at == FAKE_NOW
    notifier.booking_incomplete_at_deadline.assert_awaited_once_with(
        booking, [COMPANY_PROFILE_MISSING, BILLING_ADDRESS_MISSING]
    )
    notifier.booking_finalized.assert_not_awaited()


async def test_an_already_blocked_booking_is_not_reported_twice():
    booking = make_booking(complete=False, auto_finalize_blocked_at=FAKE_NOW)
    kp_repository = repository_with([booking])
    notifier = AsyncMock()

    await auto_finalize_bookings(kp_repository, notifier, FAKE_NOW + timedelta(hours=1))

    kp_repository.update_booking.assert_not_awaited()
    notifier.booking_incomplete_at_deadline.assert_not_awaited()


async def test_each_due_booking_is_handled_on_its_own():
    complete = make_booking()
    incomplete = make_booking(complete=False)
    kp_repository = repository_with([complete, incomplete])
    notifier = AsyncMock()

    await auto_finalize_bookings(kp_repository, notifier, FAKE_NOW)

    assert kp_repository.update_booking.await_count == 2
    notifier.booking_finalized.assert_awaited_once_with(complete)
    notifier.booking_incomplete_at_deadline.assert_awaited_once()
