from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import (
    KpBookingIncomplete,
    KpBookingStatusTransitionInvalid,
    KpFinalizationDeadlinePassed,
    NotAllowed,
)
from app.models.company import Company
from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBoothZone,
)
from app.schemas.kp import (
    RejectBookingInput,
    UpdateBookingStatusInput,
)
from app.services.booking_completeness import (
    BILLING_ADDRESS_MISSING,
    COMPANY_PROFILE_MISSING,
)
from app.services.kp_service import (
    COMPANY_BOOKING_TRANSITIONS,
    STAFF_BOOKING_TRANSITIONS,
    KpService,
)
from tests.unit.conftest import complete_company_profile, complete_company_snapshot

REJECTION_REASON = "The booth zone is not available for this company."

EXPECTED_COMPANY_TRANSITIONS = {
    KpBookingStatus.REGISTERED: {
        KpBookingStatus.FINALIZED,
        KpBookingStatus.CANCELLED,
    },
    KpBookingStatus.FINALIZED: {KpBookingStatus.CANCELLED},
    KpBookingStatus.CONFIRMED: set[KpBookingStatus](),
    KpBookingStatus.CANCELLED: set[KpBookingStatus](),
    KpBookingStatus.REJECTED: set[KpBookingStatus](),
}

EXPECTED_STAFF_TRANSITIONS = {
    KpBookingStatus.REGISTERED: {KpBookingStatus.REJECTED},
    KpBookingStatus.FINALIZED: {KpBookingStatus.CONFIRMED, KpBookingStatus.REJECTED},
    KpBookingStatus.CONFIRMED: {KpBookingStatus.FINALIZED},
    KpBookingStatus.CANCELLED: set[KpBookingStatus](),
    KpBookingStatus.REJECTED: set[KpBookingStatus](),
}

ORDERED_PAIRS = [
    (current, target) for current in KpBookingStatus for target in KpBookingStatus
]


def make_event(*, finalization_deadline: date | None = None) -> KpEvent:
    today = date.today()
    deadline = finalization_deadline or today + timedelta(days=2)
    return KpEvent(
        id=uuid4(),
        name="Kontaktparty",
        registration_open=today - timedelta(days=1),
        registration_end=today + timedelta(days=1),
        finalization_deadline=deadline,
        nametags_deadline=today + timedelta(days=3),
        event_date=today + timedelta(days=30),
    )


def make_booking(
    *,
    status: KpBookingStatus = KpBookingStatus.REGISTERED,
    company_id: UUID | None = None,
    complete: bool = True,
    event: KpEvent | None = None,
) -> KpEventBooking:
    event = event or make_event()
    booking = KpEventBooking(
        id=uuid4(),
        event_id=event.id,
        company_id=company_id or uuid4(),
        booth_zone_id=uuid4(),
        status=status,
    )
    booking.event = event
    booking.services = []
    booking.name_tags = []
    booking.upgrade_waitlist_entries = []
    booking.booth_zone = KpEventBoothZone(
        id=booking.booth_zone_id,
        event_id=event.id,
        name="Main hall",
        description="",
    )
    company = Company(id=booking.company_id, name="Acme AG")
    if complete:
        company.kp_profile = complete_company_profile(company.id)
        booking.company_details = complete_company_snapshot(booking.id)
    booking.company = company
    return booking


StaffAction = Callable[[KpService, UUID], Awaitable[Any]]

STAFF_ACTIONS: dict[KpBookingStatus, StaffAction] = {
    KpBookingStatus.CONFIRMED: lambda service, booking_id: service.accept_booking(
        booking_id
    ),
    KpBookingStatus.FINALIZED: lambda service, booking_id: service.undo_accept_booking(
        booking_id
    ),
    KpBookingStatus.REJECTED: lambda service, booking_id: service.reject_booking(
        booking_id, RejectBookingInput(reason=REJECTION_REASON)
    ),
}


def company_service(kp_repo: Any, storage_service: Any, user: Any) -> KpService:
    return KpService(kp_repo, storage_service, user)


def test_the_company_transition_table_matches_the_product_decision():
    assert {
        status: set(targets) for status, targets in COMPANY_BOOKING_TRANSITIONS.items()
    } == EXPECTED_COMPANY_TRANSITIONS


def test_the_staff_transition_table_matches_the_product_decision():
    assert {
        status: set(targets) for status, targets in STAFF_BOOKING_TRANSITIONS.items()
    } == EXPECTED_STAFF_TRANSITIONS


@pytest.mark.parametrize(("current", "target"), ORDERED_PAIRS)
async def test_company_transition_matrix(
    kp_repo: Any,
    storage_service: Any,
    make_user: Callable[..., Any],
    current: KpBookingStatus,
    target: KpBookingStatus,
):
    company_id = uuid4()
    booking = make_booking(status=current, company_id=company_id)
    service = company_service(
        kp_repo, storage_service, make_user(company_id=company_id)
    )
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.update_booking.return_value = make_booking(
        status=target, company_id=company_id
    )

    if current == target:
        result = await service.update_my_booking_status(
            booking.id, UpdateBookingStatusInput(status=target)
        )
        assert result.status == target
        kp_repo.update_booking.assert_not_awaited()
        return

    if target in EXPECTED_COMPANY_TRANSITIONS[current]:
        result = await service.update_my_booking_status(
            booking.id, UpdateBookingStatusInput(status=target)
        )
        assert result.status == target
        return

    with pytest.raises(KpBookingStatusTransitionInvalid):
        await service.update_my_booking_status(
            booking.id, UpdateBookingStatusInput(status=target)
        )
    kp_repo.update_booking.assert_not_awaited()


@pytest.mark.parametrize(("current", "target"), ORDERED_PAIRS)
async def test_staff_transition_matrix(
    kp_repo: Any,
    storage_service: Any,
    staff_user: Any,
    current: KpBookingStatus,
    target: KpBookingStatus,
):
    action = STAFF_ACTIONS.get(target)
    if action is None:
        assert target not in EXPECTED_STAFF_TRANSITIONS[current]
        return

    booking = make_booking(status=current)
    service = KpService(kp_repo, storage_service, staff_user)
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.update_booking.return_value = make_booking(status=target)

    if target in EXPECTED_STAFF_TRANSITIONS[current]:
        result = await action(service, booking.id)
        assert result.status == target
        return

    with pytest.raises(KpBookingStatusTransitionInvalid):
        await action(service, booking.id)
    kp_repo.update_booking.assert_not_awaited()


@pytest.mark.parametrize("target", sorted(STAFF_ACTIONS))
async def test_staff_transitions_are_refused_for_company_users(
    kp_repo: Any,
    storage_service: Any,
    make_user: Callable[..., Any],
    target: KpBookingStatus,
):
    booking = make_booking(status=KpBookingStatus.FINALIZED)
    service = KpService(kp_repo, storage_service, make_user(company_id=uuid4()))
    kp_repo.get_booking_by_id.return_value = booking

    with pytest.raises(NotAllowed):
        await STAFF_ACTIONS[target](service, booking.id)

    kp_repo.update_booking.assert_not_awaited()


async def test_finalize_records_the_finalized_timestamp(
    kp_repo: Any, storage_service: Any, make_user: Callable[..., Any]
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    service = company_service(
        kp_repo, storage_service, make_user(company_id=company_id)
    )
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.update_booking.return_value = make_booking(
        status=KpBookingStatus.FINALIZED, company_id=company_id
    )

    await service.update_my_booking_status(
        booking.id, UpdateBookingStatusInput(status=KpBookingStatus.FINALIZED)
    )

    update = kp_repo.update_booking.await_args.args[1]
    assert update.status_changed_at is not None
    assert update.finalized_at == update.status_changed_at
    assert update.confirmed_at is None


async def test_cancel_records_only_the_status_change(
    kp_repo: Any, storage_service: Any, make_user: Callable[..., Any]
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    service = company_service(
        kp_repo, storage_service, make_user(company_id=company_id)
    )
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.update_booking.return_value = make_booking(
        status=KpBookingStatus.CANCELLED, company_id=company_id
    )

    await service.update_my_booking_status(
        booking.id, UpdateBookingStatusInput(status=KpBookingStatus.CANCELLED)
    )

    update = kp_repo.update_booking.await_args.args[1]
    assert update.status_changed_at is not None
    assert "finalized_at" not in update.model_dump(exclude_unset=True)


async def test_accept_records_the_confirmed_timestamp(
    kp_repo: Any, storage_service: Any, staff_user: Any
):
    booking = make_booking(status=KpBookingStatus.FINALIZED)
    service = KpService(kp_repo, storage_service, staff_user)
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.update_booking.return_value = make_booking(status=KpBookingStatus.CONFIRMED)

    await service.accept_booking(booking.id)

    update = kp_repo.update_booking.await_args.args[1]
    assert update.confirmed_at == update.status_changed_at


async def test_undo_accept_clears_the_confirmed_timestamp(
    kp_repo: Any, storage_service: Any, staff_user: Any
):
    booking = make_booking(status=KpBookingStatus.CONFIRMED)
    service = KpService(kp_repo, storage_service, staff_user)
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.update_booking.return_value = make_booking(status=KpBookingStatus.FINALIZED)

    await service.undo_accept_booking(booking.id)

    update = kp_repo.update_booking.await_args.args[1]
    assert update.confirmed_at is None
    assert "finalized_at" not in update.model_fields_set


async def test_reject_stores_the_reason(
    kp_repo: Any, storage_service: Any, staff_user: Any
):
    booking = make_booking(status=KpBookingStatus.FINALIZED)
    service = KpService(kp_repo, storage_service, staff_user)
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.update_booking.return_value = make_booking(status=KpBookingStatus.REJECTED)

    await service.reject_booking(
        booking.id, RejectBookingInput(reason=REJECTION_REASON)
    )

    update = kp_repo.update_booking.await_args.args[1]
    assert update.rejection_reason == REJECTION_REASON


async def test_finalize_refuses_an_incomplete_booking(
    kp_repo: Any, storage_service: Any, make_user: Callable[..., Any]
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id, complete=False)
    service = company_service(
        kp_repo, storage_service, make_user(company_id=company_id)
    )
    kp_repo.get_booking_by_id.return_value = booking

    with pytest.raises(KpBookingIncomplete) as error:
        await service.update_my_booking_status(
            booking.id, UpdateBookingStatusInput(status=KpBookingStatus.FINALIZED)
        )

    assert error.value.status_code == 409
    assert error.value.code == "error.kp_booking_incomplete"
    assert error.value.details == {
        "missingItems": [COMPANY_PROFILE_MISSING, BILLING_ADDRESS_MISSING]
    }
    kp_repo.update_booking.assert_not_awaited()


async def test_finalize_after_the_deadline_is_refused_before_completeness(
    kp_repo: Any, storage_service: Any, make_user: Callable[..., Any]
):
    company_id = uuid4()
    booking = make_booking(
        company_id=company_id,
        complete=False,
        event=make_event(finalization_deadline=date.today() - timedelta(days=1)),
    )
    service = company_service(
        kp_repo, storage_service, make_user(company_id=company_id)
    )
    kp_repo.get_booking_by_id.return_value = booking

    with pytest.raises(KpFinalizationDeadlinePassed):
        await service.update_my_booking_status(
            booking.id, UpdateBookingStatusInput(status=KpBookingStatus.FINALIZED)
        )


async def test_cancel_stays_allowed_after_the_deadline(
    kp_repo: Any, storage_service: Any, make_user: Callable[..., Any]
):
    company_id = uuid4()
    event = make_event(finalization_deadline=date.today() - timedelta(days=1))
    booking = make_booking(company_id=company_id, event=event)
    service = company_service(
        kp_repo, storage_service, make_user(company_id=company_id)
    )
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.update_booking.return_value = make_booking(
        status=KpBookingStatus.CANCELLED, company_id=company_id, event=event
    )

    result = await service.update_my_booking_status(
        booking.id, UpdateBookingStatusInput(status=KpBookingStatus.CANCELLED)
    )

    assert result.status == KpBookingStatus.CANCELLED


@pytest.mark.parametrize("reason", ["short", "   " + "x" * 5 + "  ", "y" * 1001])
def test_rejection_reason_length_is_enforced(reason: str):
    with pytest.raises(ValueError):
        RejectBookingInput(reason=reason)
