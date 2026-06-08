from dataclasses import dataclass
from datetime import date, timedelta
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    KpBookingAlreadyExists,
    KpBookingConfirmationRequiresFinalized,
    KpBookingNotFound,
    KpBookingStatusTransitionInvalid,
    KpBoothZoneAtCapacity,
    KpBoothZoneEventMismatch,
    KpEventNotFound,
    KpNameExists,
    KpRegistrationClosed,
    KpRequirementFileUploadNotAllowed,
    KpRequirementTextAnswerNotAllowed,
    KpServiceQuantityInvalid,
    KpServiceRequirementNotFound,
    KpServiceUnavailable,
    KpWaitlistSameZone,
    NotAllowed,
)
from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventRegistrationException,
    KpEventService,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
)
from app.models.storage import StoredFile
from app.schemas.kp import (
    BookingServiceInput,
    CloneKpInput,
    CreateKpInput,
    UpdateBookingInput,
    UpdateBookingStatusInput,
)
from app.services.kp_service import KpService
from app.services.storage_service import StoredObject


@dataclass
class KpServiceHarness:
    service: KpService
    kp_repo: AsyncMock
    storage_service: AsyncMock


@pytest.fixture
def kp_service(kp_repo, storage_service, admin_user):
    return KpServiceHarness(
        service=KpService(kp_repo, storage_service, admin_user),
        kp_repo=kp_repo,
        storage_service=storage_service,
    )


def make_event(*, event_id=None, name: str = "Kontaktparty") -> KpEvent:
    today = date.today()
    return KpEvent(
        id=event_id or uuid4(),
        name=name,
        registration_open=today - timedelta(days=1),
        registration_end=today + timedelta(days=1),
        finalization_deadline=today + timedelta(days=2),
        nametags_deadline=today + timedelta(days=3),
        event_date=today + timedelta(days=10),
    )


def make_closed_event(*, event_id=None, name: str = "Kontaktparty") -> KpEvent:
    today = date.today()
    return KpEvent(
        id=event_id or uuid4(),
        name=name,
        registration_open=today - timedelta(days=10),
        registration_end=today - timedelta(days=5),
        finalization_deadline=today - timedelta(days=4),
        nametags_deadline=today - timedelta(days=3),
        event_date=today + timedelta(days=10),
    )


def make_zone(*, event_id, zone_id=None, capacity: int = 2) -> KpEventBoothZone:
    return KpEventBoothZone(
        id=zone_id or uuid4(),
        event_id=event_id,
        name="Main Hall",
        description="Main booth zone",
        capacity=capacity,
    )


def make_booking(
    *,
    event_id=None,
    company_id=None,
    booth_zone_id=None,
    status: KpBookingStatus = KpBookingStatus.REGISTERED,
) -> KpEventBooking:
    return KpEventBooking(
        id=uuid4(),
        event_id=event_id or uuid4(),
        company_id=company_id or uuid4(),
        booth_zone_id=booth_zone_id or uuid4(),
        status=status,
    )


def make_booking_service(
    *,
    booking: KpEventBooking,
    service_id=None,
) -> KpEventBookingService:
    return KpEventBookingService(
        id=uuid4(),
        booking_id=booking.id,
        service_id=service_id or uuid4(),
        booking=booking,
    )


def make_requirement(
    *,
    service_id,
    requirement_type: KpEventServiceRequirementType = KpEventServiceRequirementType.PDF,
) -> KpEventServiceRequirement:
    return KpEventServiceRequirement(
        id=uuid4(),
        service_id=service_id,
        type=requirement_type,
        name="Upload file",
        description="Please upload the requested file.",
    )


def make_service(
    *,
    event_id,
    service_id=None,
    is_active: bool = True,
    max_quantity_per_booking: int = 3,
    max_total_quantity: int = 0,
) -> KpEventService:
    return KpEventService(
        id=service_id or uuid4(),
        event_id=event_id,
        name="Power",
        description="Power connection",
        price=10000,
        is_active=is_active,
        max_quantity_per_booking=max_quantity_per_booking,
        max_total_quantity=max_total_quantity,
    )


def make_stored_file(storage_key: str = "old/key.pdf") -> StoredFile:
    return StoredFile(
        id=uuid4(),
        storage_key=storage_key,
        original_filename="old.pdf",
        mime_type="application/pdf",
        size_bytes=7,
        sha256="a" * 64,
        etag="old-etag",
    )


def make_requirement_file(
    *,
    booking_service: KpEventBookingService,
    requirement: KpEventServiceRequirement,
    stored_file: StoredFile | None = None,
) -> KpEventBookingServiceFileLink:
    stored_file = stored_file or make_stored_file()
    return KpEventBookingServiceFileLink(
        id=uuid4(),
        booking_service_id=booking_service.id,
        requirement_id=requirement.id,
        stored_file_id=stored_file.id,
        booking_service=booking_service,
        requirement=requirement,
        stored_file=stored_file,
    )


def make_create_kp_input(name: str = "Kontaktparty") -> CreateKpInput:
    event = make_event(name=name)
    return CreateKpInput(
        name=event.name,
        registration_open=event.registration_open,
        registration_end=event.registration_end,
        finalization_deadline=event.finalization_deadline,
        nametags_deadline=event.nametags_deadline,
        event_date=event.event_date,
    )


def make_clone_kp_input(name: str = "Kontaktparty Clone") -> CloneKpInput:
    event = make_event(name=name)
    return CloneKpInput(
        name=event.name,
        registration_open=event.registration_open,
        registration_end=event.registration_end,
        finalization_deadline=event.finalization_deadline,
        nametags_deadline=event.nametags_deadline,
        event_date=event.event_date,
    )


async def test_create_kp_rejects_duplicate_name(kp_service):
    create_input = make_create_kp_input(name="Kontaktparty")
    kp_service.kp_repo.get_by_name.return_value = make_event(name="Kontaktparty")

    with pytest.raises(KpNameExists):
        await kp_service.service.create_kp(create_input)

    kp_service.kp_repo.create_kp.assert_not_awaited()


async def test_create_kp_delegates_to_repository(kp_service):
    create_input = make_create_kp_input(name="Kontaktparty")
    event = make_event(name="Kontaktparty")
    kp_service.kp_repo.get_by_name.return_value = None
    kp_service.kp_repo.create_kp.return_value = event

    result = await kp_service.service.create_kp(create_input)

    assert result is event
    kp_service.kp_repo.create_kp.assert_awaited_once_with(create_input)


async def test_clone_kp_rejects_missing_source(kp_service):
    clone_input = make_clone_kp_input()
    kp_service.kp_repo.get_by_name.return_value = None
    kp_service.kp_repo.clone_kp.return_value = None

    with pytest.raises(KpEventNotFound):
        await kp_service.service.clone_kp(uuid4(), clone_input)

    kp_service.kp_repo.clone_kp.assert_awaited_once()


async def test_clone_kp_rejects_duplicate_name(kp_service):
    event = make_event()
    clone_input = make_clone_kp_input(name="Kontaktparty Clone")
    kp_service.kp_repo.get_by_name.return_value = make_event(name=clone_input.name)

    with pytest.raises(KpNameExists):
        await kp_service.service.clone_kp(event.id, clone_input)

    kp_service.kp_repo.clone_kp.assert_not_awaited()


async def test_clone_kp_delegates_to_repository(kp_service):
    event = make_event()
    clone_input = make_clone_kp_input(name="Kontaktparty Clone")
    cloned_event = make_event(name=clone_input.name)
    kp_service.kp_repo.get_by_name.return_value = None
    kp_service.kp_repo.clone_kp.return_value = cloned_event

    result = await kp_service.service.clone_kp(event.id, clone_input)

    assert result is cloned_event
    kp_service.kp_repo.clone_kp.assert_awaited_once_with(event.id, clone_input)


async def test_register_booking_creates_booking_when_zone_has_capacity(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    event = make_event()
    zone = make_zone(event_id=event.id, capacity=2)
    user = make_user(company_id=company_id)
    service = KpService(kp_repo, storage_service, user)
    booking = make_booking(
        event_id=event.id,
        company_id=company_id,
        booth_zone_id=zone.id,
    )
    kp_repo.get_by_id.return_value = event
    kp_repo.get_booth_zone_by_id.return_value = zone
    kp_repo.get_company_active_booking_for_event.return_value = None
    kp_repo.lock_model_by_id.side_effect = [event, zone]
    kp_repo.count_active_bookings_for_zone.return_value = 1
    kp_repo.create_booking.return_value = booking

    result = await service.register_booking(event.id, zone.id)

    assert result.id == booking.id
    assert result.event_id == booking.event_id
    kp_repo.create_booking.assert_awaited_once()
    kwargs = kp_repo.create_booking.await_args.kwargs
    assert kwargs["event_id"] == event.id
    assert kwargs["company_id"] == company_id
    assert kwargs["booth_zone_id"] == zone.id
    assert kwargs["create_booking_input"].status == KpBookingStatus.REGISTERED


async def test_list_available_services_for_company_returns_active_only(
    kp_repo,
    storage_service,
    make_user,
):
    event = make_event()
    active_service = make_service(event_id=event.id, is_active=True)
    inactive_service = make_service(event_id=event.id, is_active=False)
    service = KpService(kp_repo, storage_service, make_user(company_id=uuid4()))
    kp_repo.get_by_id.return_value = event
    kp_repo.list_services.return_value = [active_service, inactive_service]

    result = await service.list_available_services_for_company(event.id)

    assert [item.id for item in result] == [active_service.id]
    assert result[0].name == active_service.name
    kp_repo.list_services.assert_awaited_once_with(event.id)


async def test_register_booking_creates_selected_services(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    event = make_event()
    zone = make_zone(event_id=event.id, capacity=2)
    extra_service = make_service(event_id=event.id)
    user = make_user(company_id=company_id)
    service = KpService(kp_repo, storage_service, user)
    booking = make_booking(
        event_id=event.id,
        company_id=company_id,
        booth_zone_id=zone.id,
    )
    kp_repo.get_by_id.return_value = event
    kp_repo.get_booth_zone_by_id.return_value = zone
    kp_repo.get_company_active_booking_for_event.return_value = None
    kp_repo.lock_model_by_id.side_effect = [event, zone]
    kp_repo.count_active_bookings_for_zone.return_value = 0
    kp_repo.get_service_by_id.return_value = extra_service
    kp_repo.count_active_service_quantity.return_value = 1
    kp_repo.create_booking.return_value = booking
    selected_services = [
        BookingServiceInput(service_id=extra_service.id, quantity=2),
    ]

    result = await service.register_booking(event.id, zone.id, selected_services)

    assert result.id == booking.id
    assert result.event_id == booking.event_id
    kwargs = kp_repo.create_booking.await_args.kwargs
    assert kwargs["services"] == selected_services


async def test_register_booking_rejects_inactive_service(
    kp_repo,
    storage_service,
    make_user,
):
    event = make_event()
    zone = make_zone(event_id=event.id, capacity=2)
    inactive_service = make_service(event_id=event.id, is_active=False)
    service = KpService(kp_repo, storage_service, make_user(company_id=uuid4()))
    kp_repo.get_by_id.return_value = event
    kp_repo.get_booth_zone_by_id.return_value = zone
    kp_repo.get_company_active_booking_for_event.return_value = None
    kp_repo.lock_model_by_id.side_effect = [event, zone]
    kp_repo.count_active_bookings_for_zone.return_value = 0
    kp_repo.get_service_by_id.return_value = inactive_service

    with pytest.raises(KpServiceUnavailable):
        await service.register_booking(
            event.id,
            zone.id,
            [BookingServiceInput(service_id=inactive_service.id, quantity=1)],
        )

    kp_repo.create_booking.assert_not_awaited()


async def test_register_booking_rejects_service_quantity_over_booking_limit(
    kp_repo,
    storage_service,
    make_user,
):
    event = make_event()
    zone = make_zone(event_id=event.id, capacity=2)
    extra_service = make_service(event_id=event.id, max_quantity_per_booking=1)
    service = KpService(kp_repo, storage_service, make_user(company_id=uuid4()))
    kp_repo.get_by_id.return_value = event
    kp_repo.get_booth_zone_by_id.return_value = zone
    kp_repo.get_company_active_booking_for_event.return_value = None
    kp_repo.lock_model_by_id.side_effect = [event, zone]
    kp_repo.count_active_bookings_for_zone.return_value = 0
    kp_repo.get_service_by_id.return_value = extra_service

    with pytest.raises(KpServiceQuantityInvalid):
        await service.register_booking(
            event.id,
            zone.id,
            [BookingServiceInput(service_id=extra_service.id, quantity=2)],
        )

    kp_repo.create_booking.assert_not_awaited()


async def test_register_booking_rejects_existing_active_booking(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    event = make_event()
    zone = make_zone(event_id=event.id)
    user = make_user(company_id=company_id)
    service = KpService(kp_repo, storage_service, user)
    kp_repo.get_by_id.return_value = event
    kp_repo.lock_model_by_id.return_value = event
    kp_repo.get_booth_zone_by_id.return_value = zone
    kp_repo.get_company_active_booking_for_event.return_value = make_booking(
        event_id=event.id,
        company_id=company_id,
        booth_zone_id=zone.id,
    )

    with pytest.raises(KpBookingAlreadyExists):
        await service.register_booking(event.id, zone.id)

    kp_repo.create_booking.assert_not_awaited()


async def test_register_booking_rejects_full_zone(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    event = make_event()
    zone = make_zone(event_id=event.id, capacity=1)
    user = make_user(company_id=company_id)
    service = KpService(kp_repo, storage_service, user)
    kp_repo.get_by_id.return_value = event
    kp_repo.get_booth_zone_by_id.return_value = zone
    kp_repo.get_company_active_booking_for_event.return_value = None
    kp_repo.lock_model_by_id.side_effect = [event, zone]
    kp_repo.count_active_bookings_for_zone.return_value = 1

    with pytest.raises(KpBoothZoneAtCapacity):
        await service.register_booking(event.id, zone.id)

    kp_repo.create_booking.assert_not_awaited()


async def test_register_booking_rejects_closed_registration(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    event = make_closed_event()
    zone = make_zone(event_id=event.id)
    user = make_user(company_id=company_id)
    service = KpService(kp_repo, storage_service, user)
    kp_repo.get_by_id.return_value = event
    kp_repo.get_registration_exception.return_value = None
    kp_repo.get_booth_zone_by_id.return_value = zone

    with pytest.raises(KpRegistrationClosed):
        await service.register_booking(event.id, zone.id)

    kp_repo.lock_model_by_id.assert_not_awaited()
    kp_repo.create_booking.assert_not_awaited()


async def test_register_booking_allows_registration_exception(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    event = make_closed_event()
    zone = make_zone(event_id=event.id, capacity=1)
    user = make_user(company_id=company_id)
    service = KpService(kp_repo, storage_service, user)
    exception = KpEventRegistrationException(
        event_id=event.id,
        company_id=company_id,
        allowed_until=date.today(),
    )
    booking = make_booking(
        event_id=event.id,
        company_id=company_id,
        booth_zone_id=zone.id,
    )
    kp_repo.get_by_id.return_value = event
    kp_repo.get_registration_exception.return_value = exception
    kp_repo.get_booth_zone_by_id.return_value = zone
    kp_repo.get_company_active_booking_for_event.return_value = None
    kp_repo.lock_model_by_id.side_effect = [event, zone]
    kp_repo.count_active_bookings_for_zone.return_value = 0
    kp_repo.create_booking.return_value = booking

    result = await service.register_booking(event.id, zone.id)

    assert result.id == booking.id
    assert result.event_id == booking.event_id
    kp_repo.create_booking.assert_awaited_once()


async def test_register_booking_rejects_zone_from_different_event(
    kp_repo,
    storage_service,
    make_user,
):
    event = make_event()
    zone = make_zone(event_id=uuid4())
    service = KpService(kp_repo, storage_service, make_user(company_id=uuid4()))
    kp_repo.get_by_id.return_value = event
    kp_repo.get_booth_zone_by_id.return_value = zone

    with pytest.raises(KpBoothZoneEventMismatch):
        await service.register_booking(event.id, zone.id)

    kp_repo.create_booking.assert_not_awaited()


async def test_update_my_booking_status_rejects_invalid_company_transition(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id, status=KpBookingStatus.REGISTERED)
    user = make_user(company_id=company_id)
    service = KpService(kp_repo, storage_service, user)
    kp_repo.get_booking_by_id.return_value = booking

    with pytest.raises(KpBookingStatusTransitionInvalid):
        await service.update_my_booking_status(
            booking.id,
            UpdateBookingStatusInput(status=KpBookingStatus.CONFIRMED),
        )

    kp_repo.update_booking.assert_not_awaited()


async def test_update_my_booking_status_allows_valid_company_transition(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id, status=KpBookingStatus.REGISTERED)
    updated = make_booking(company_id=company_id, status=KpBookingStatus.FINALIZED)
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.update_booking.return_value = updated

    result = await service.update_my_booking_status(
        booking.id,
        UpdateBookingStatusInput(status=KpBookingStatus.FINALIZED),
    )

    assert result is updated
    args = kp_repo.update_booking.await_args.args
    assert args[0] is booking
    assert args[1].status == KpBookingStatus.FINALIZED


async def test_replace_booking_upgrade_waitlist_deduplicates_target_zones(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    event_id = uuid4()
    current_zone_id = uuid4()
    target_zone_a = make_zone(event_id=event_id)
    target_zone_b = make_zone(event_id=event_id)
    booking = make_booking(
        event_id=event_id,
        company_id=company_id,
        booth_zone_id=current_zone_id,
    )
    waitlist = [
        KpEventBookingUpgradeWaitlist(
            booking_id=booking.id,
            target_booth_zone_id=target_zone_a.id,
        )
    ]
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.get_booth_zone_by_id.side_effect = [target_zone_a, target_zone_b]
    kp_repo.replace_booking_upgrade_waitlist_entries.return_value = waitlist

    result = await service.replace_booking_upgrade_waitlist(
        booking.id,
        [target_zone_a.id, target_zone_a.id, target_zone_b.id],
    )

    assert result == waitlist
    kp_repo.replace_booking_upgrade_waitlist_entries.assert_awaited_once_with(
        booking=booking,
        target_booth_zone_ids=[target_zone_a.id, target_zone_b.id],
    )


async def test_replace_booking_upgrade_waitlist_rejects_current_zone(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    event_id = uuid4()
    current_zone = make_zone(event_id=event_id)
    booking = make_booking(
        event_id=event_id,
        company_id=company_id,
        booth_zone_id=current_zone.id,
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_by_id.return_value = booking
    kp_repo.get_booth_zone_by_id.return_value = current_zone

    with pytest.raises(KpWaitlistSameZone):
        await service.replace_booking_upgrade_waitlist(booking.id, [current_zone.id])

    kp_repo.replace_booking_upgrade_waitlist_entries.assert_not_awaited()


async def test_get_event_booking_returns_matching_booking(kp_service):
    event = make_event()
    booking = make_booking(event_id=event.id)
    kp_service.kp_repo.get_by_id.return_value = event
    kp_service.kp_repo.get_booking_by_id.return_value = booking

    result = await kp_service.service.get_event_booking(event.id, booking.id)

    assert result is booking
    kp_service.kp_repo.get_booking_by_id.assert_awaited_once_with(booking.id)


async def test_get_event_booking_rejects_booking_from_other_event(kp_service):
    event = make_event()
    booking = make_booking(event_id=uuid4())
    kp_service.kp_repo.get_by_id.return_value = event
    kp_service.kp_repo.get_booking_by_id.return_value = booking

    with pytest.raises(KpBookingNotFound):
        await kp_service.service.get_event_booking(event.id, booking.id)


async def test_confirm_booking_requires_finalized_booking(kp_service):
    booking = make_booking(status=KpBookingStatus.REGISTERED)
    kp_service.kp_repo.get_booking_by_id.return_value = booking

    with pytest.raises(KpBookingConfirmationRequiresFinalized):
        await kp_service.service.confirm_booking(booking.id)

    kp_service.kp_repo.update_booking.assert_not_awaited()


async def test_confirm_booking_sets_confirmed_status(kp_service):
    booking = make_booking(status=KpBookingStatus.FINALIZED)
    confirmed = make_booking(status=KpBookingStatus.CONFIRMED)
    kp_service.kp_repo.get_booking_by_id.return_value = booking
    kp_service.kp_repo.update_booking.return_value = confirmed

    result = await kp_service.service.confirm_booking(booking.id)

    assert result is confirmed
    kp_service.kp_repo.update_booking.assert_awaited_once()
    args = kp_service.kp_repo.update_booking.await_args.args
    assert args[0] is booking
    assert isinstance(args[1], UpdateBookingInput)
    assert args[1].status == KpBookingStatus.CONFIRMED


async def test_delete_service_image_keeps_stored_file_row_when_storage_delete_fails(
    kp_repo,
    storage_service,
    admin_user,
):
    event_id = uuid4()
    stored_file = make_stored_file("services/image.png")
    service_model = make_service(event_id=event_id)
    service_model.image_stored_file_id = stored_file.id
    service_model.image_stored_file = stored_file
    kp_repo.get_service_by_id.return_value = service_model
    kp_repo.set_service_image_stored_file_id.return_value = service_model
    storage_service.delete_object.side_effect = RuntimeError("s3 failed")
    service = KpService(kp_repo, storage_service, admin_user)

    with pytest.raises(RuntimeError):
        await service.delete_service_image(service_model.id)

    kp_repo.set_service_image_stored_file_id.assert_awaited_once_with(
        service_model, None
    )
    storage_service.delete_object.assert_awaited_once_with("services/image.png")
    kp_repo.delete_stored_file.assert_not_awaited()


async def test_upload_booking_requirement_file_rejects_text_requirement(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(
        service_id=booking_service.service_id,
        requirement_type=KpEventServiceRequirementType.TEXT,
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement

    with pytest.raises(KpRequirementFileUploadNotAllowed):
        await service.upload_booking_requirement_file(
            booking_service.id,
            requirement.id,
            "notes.txt",
            b"text",
            "text/plain",
        )

    storage_service.upload_bytes.assert_not_awaited()


async def test_upsert_booking_requirement_text_saves_text_answer(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(
        service_id=booking_service.service_id,
        requirement_type=KpEventServiceRequirementType.TEXT,
    )
    requirement_answer = KpEventBookingServiceFileLink(
        id=uuid4(),
        booking_service_id=booking_service.id,
        requirement_id=requirement.id,
        text_value="Please use the attached slogan.",
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = None
    kp_repo.upsert_requirement_text_answer.return_value = requirement_answer

    result = await service.upsert_booking_requirement_text(
        booking_service.id,
        requirement.id,
        "  Please use the attached slogan.  ",
    )

    assert result.text_value == "Please use the attached slogan."
    kp_repo.upsert_requirement_text_answer.assert_awaited_once_with(
        booking_service_id=booking_service.id,
        requirement_id=requirement.id,
        text_value="Please use the attached slogan.",
    )
    storage_service.delete_object.assert_not_awaited()


async def test_upsert_booking_requirement_text_deletes_replaced_file(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(
        service_id=booking_service.service_id,
        requirement_type=KpEventServiceRequirementType.TEXT,
    )
    old_file = make_stored_file("old/key.txt")
    existing_file = make_requirement_file(
        booking_service=booking_service,
        requirement=requirement,
        stored_file=old_file,
    )
    requirement_answer = KpEventBookingServiceFileLink(
        id=existing_file.id,
        booking_service_id=booking_service.id,
        requirement_id=requirement.id,
        text_value="Updated notes.",
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = existing_file
    kp_repo.upsert_requirement_text_answer.return_value = requirement_answer

    result = await service.upsert_booking_requirement_text(
        booking_service.id,
        requirement.id,
        "Updated notes.",
    )

    assert result.text_value == "Updated notes."
    storage_service.delete_object.assert_awaited_once_with("old/key.txt")
    kp_repo.delete_stored_file.assert_awaited_once_with(old_file)


async def test_upsert_booking_requirement_text_rejects_file_requirement(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(
        service_id=booking_service.service_id,
        requirement_type=KpEventServiceRequirementType.PDF,
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement

    with pytest.raises(KpRequirementTextAnswerNotAllowed):
        await service.upsert_booking_requirement_text(
            booking_service.id,
            requirement.id,
            "Not allowed here",
        )

    kp_repo.upsert_requirement_text_answer.assert_not_awaited()


async def test_upload_booking_requirement_file_replaces_existing_text_answer(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(service_id=booking_service.service_id)
    existing_text = KpEventBookingServiceFileLink(
        id=uuid4(),
        booking_service_id=booking_service.id,
        requirement_id=requirement.id,
        text_value="Old notes.",
    )
    stored_object = StoredObject(
        key="new/key.pdf",
        etag="new-etag",
        mime_type="application/pdf",
        size_bytes=7,
        sha256="b" * 64,
    )
    stored_file = make_stored_file("new/key.pdf")
    requirement_file = make_requirement_file(
        booking_service=booking_service,
        requirement=requirement,
        stored_file=stored_file,
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = existing_text
    storage_service.validate_pdf_file.return_value = "application/pdf"
    storage_service.upload_bytes.return_value = stored_object
    kp_repo.upsert_stored_file.return_value = stored_file
    kp_repo.upsert_requirement_file_link.return_value = requirement_file

    result = await service.upload_booking_requirement_file(
        booking_service.id,
        requirement.id,
        "document.pdf",
        b"content",
        "application/pdf",
    )

    assert result is requirement_file
    kp_repo.upsert_stored_file.assert_awaited_once_with(
        storage_key="new/key.pdf",
        original_filename="document.pdf",
        mime_type="application/pdf",
        size_bytes=7,
        sha256="b" * 64,
        etag="new-etag",
        stored_file=None,
    )
    storage_service.delete_object.assert_not_awaited()


async def test_upload_booking_requirement_file_routes_pdf_validation_and_saves_link(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(service_id=booking_service.service_id)
    stored_object = StoredObject(
        key="new/key.pdf",
        etag="new-etag",
        mime_type="application/pdf",
        size_bytes=7,
        sha256="b" * 64,
    )
    stored_file = make_stored_file("new/key.pdf")
    requirement_file = make_requirement_file(
        booking_service=booking_service,
        requirement=requirement,
        stored_file=stored_file,
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = None
    storage_service.validate_pdf_file.return_value = "application/pdf"
    storage_service.upload_bytes.return_value = stored_object
    kp_repo.upsert_stored_file.return_value = stored_file
    kp_repo.upsert_requirement_file_link.return_value = requirement_file

    result = await service.upload_booking_requirement_file(
        booking_service.id,
        requirement.id,
        "document.pdf",
        b"content",
        "application/pdf",
    )

    assert result is requirement_file
    storage_service.validate_pdf_file.assert_called_once_with(
        "document.pdf",
        b"content",
        "application/pdf",
        error_context=f"booking_requirement:pdf:{requirement.id}",
    )
    storage_service.upload_bytes.assert_awaited_once_with(
        key=ANY,
        content=b"content",
        filename="document.pdf",
        content_type="application/pdf",
    )
    upload_key = storage_service.upload_bytes.await_args.kwargs["key"]
    assert upload_key.startswith(
        f"kp/booking-services/{booking_service.id}/requirements/{requirement.id}/"
    )
    assert upload_key.endswith(".pdf")
    kp_repo.upsert_requirement_file_link.assert_awaited_once_with(
        booking_service_id=booking_service.id,
        requirement_id=requirement.id,
        stored_file_id=stored_file.id,
    )


async def test_upload_booking_requirement_file_deletes_new_upload_when_db_write_fails(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(service_id=booking_service.service_id)
    stored_object = StoredObject(
        key="new/key.pdf",
        etag="new-etag",
        mime_type="application/pdf",
        size_bytes=7,
        sha256="b" * 64,
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = None
    storage_service.validate_pdf_file.return_value = "application/pdf"
    storage_service.upload_bytes.return_value = stored_object
    kp_repo.upsert_stored_file.side_effect = RuntimeError("db failed")

    with pytest.raises(RuntimeError):
        await service.upload_booking_requirement_file(
            booking_service.id,
            requirement.id,
            "document.pdf",
            b"content",
            "application/pdf",
        )

    storage_service.delete_object.assert_awaited_once_with("new/key.pdf")


async def test_upload_booking_requirement_file_deletes_replaced_old_file(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(service_id=booking_service.service_id)
    old_file = make_stored_file("old/key.pdf")
    existing_file = make_requirement_file(
        booking_service=booking_service,
        requirement=requirement,
        stored_file=old_file,
    )
    stored_object = StoredObject(
        key="new/key.pdf",
        etag="new-etag",
        mime_type="application/pdf",
        size_bytes=7,
        sha256="b" * 64,
    )
    updated_file = make_stored_file("new/key.pdf")
    requirement_file = make_requirement_file(
        booking_service=booking_service,
        requirement=requirement,
        stored_file=updated_file,
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = existing_file
    storage_service.validate_pdf_file.return_value = "application/pdf"
    storage_service.upload_bytes.return_value = stored_object
    kp_repo.upsert_stored_file.return_value = updated_file
    kp_repo.upsert_requirement_file_link.return_value = requirement_file

    result = await service.upload_booking_requirement_file(
        booking_service.id,
        requirement.id,
        "document.pdf",
        b"content",
        "application/pdf",
    )

    assert result is requirement_file
    storage_service.delete_object.assert_awaited_once_with("old/key.pdf")
    kp_repo.upsert_stored_file.assert_awaited_once_with(
        storage_key="new/key.pdf",
        original_filename="document.pdf",
        mime_type="application/pdf",
        size_bytes=7,
        sha256="b" * 64,
        etag="new-etag",
        stored_file=None,
    )
    kp_repo.delete_stored_file.assert_awaited_once_with(old_file)


async def test_upload_booking_requirement_file_keeps_old_row_when_old_delete_fails(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(service_id=booking_service.service_id)
    old_file = make_stored_file("old/key.pdf")
    existing_file = make_requirement_file(
        booking_service=booking_service,
        requirement=requirement,
        stored_file=old_file,
    )
    stored_object = StoredObject(
        key="new/key.pdf",
        etag="new-etag",
        mime_type="application/pdf",
        size_bytes=7,
        sha256="b" * 64,
    )
    updated_file = make_stored_file("new/key.pdf")
    requirement_file = make_requirement_file(
        booking_service=booking_service,
        requirement=requirement,
        stored_file=updated_file,
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = existing_file
    storage_service.validate_pdf_file.return_value = "application/pdf"
    storage_service.upload_bytes.return_value = stored_object
    storage_service.delete_object.side_effect = RuntimeError("s3 failed")
    kp_repo.upsert_stored_file.return_value = updated_file
    kp_repo.upsert_requirement_file_link.return_value = requirement_file

    with pytest.raises(RuntimeError):
        await service.upload_booking_requirement_file(
            booking_service.id,
            requirement.id,
            "document.pdf",
            b"content",
            "application/pdf",
        )

    storage_service.delete_object.assert_awaited_once_with("old/key.pdf")
    kp_repo.delete_stored_file.assert_not_awaited()


async def test_get_booking_requirement_file_download_url_rejects_missing_file(
    kp_repo,
    storage_service,
    make_user,
):
    company_id = uuid4()
    booking = make_booking(company_id=company_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(service_id=booking_service.service_id)
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = None

    with pytest.raises(KpServiceRequirementNotFound):
        await service.get_booking_requirement_file_download_url(
            booking_service.id,
            requirement.id,
        )

    storage_service.generate_download_url.assert_not_awaited()


async def test_staff_get_booking_requirement_file_download_url(
    kp_repo,
    storage_service,
    staff_user,
):
    booking = make_booking()
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(service_id=booking_service.service_id)
    stored_file = make_stored_file("uploads/file.pdf")
    requirement_file = make_requirement_file(
        booking_service=booking_service,
        requirement=requirement,
        stored_file=stored_file,
    )
    service = KpService(kp_repo, storage_service, staff_user)
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = requirement_file
    storage_service.generate_download_url.return_value = "https://files.example/file"

    result = await service.get_staff_booking_requirement_file_download_url(
        booking_service.id,
        requirement.id,
    )

    assert result == "https://files.example/file"
    storage_service.generate_download_url.assert_awaited_once_with(
        "uploads/file.pdf",
        stored_file.original_filename,
    )


async def test_staff_get_booking_requirement_file_rejects_company_user(
    kp_repo,
    storage_service,
    make_user,
):
    service = KpService(kp_repo, storage_service, make_user(company_id=uuid4()))

    with pytest.raises(NotAllowed):
        await service.get_staff_booking_requirement_file(uuid4(), uuid4())

    kp_repo.get_booking_service_by_id.assert_not_awaited()


async def test_staff_get_booking_requirement_file_download_url_rejects_missing_file(
    kp_repo,
    storage_service,
    staff_user,
):
    booking = make_booking()
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(service_id=booking_service.service_id)
    service = KpService(kp_repo, storage_service, staff_user)
    kp_repo.get_booking_service_by_id.return_value = booking_service
    kp_repo.get_service_requirement_by_id.return_value = requirement
    kp_repo.get_requirement_file.return_value = None

    with pytest.raises(KpServiceRequirementNotFound):
        await service.get_staff_booking_requirement_file_download_url(
            booking_service.id,
            requirement.id,
        )

    storage_service.generate_download_url.assert_not_awaited()


async def test_list_staff_booking_requirement_files_returns_file_map(
    kp_repo,
    storage_service,
    staff_user,
):
    event_id = uuid4()
    booking = make_booking(event_id=event_id)
    booking_service = make_booking_service(booking=booking)
    requirement = make_requirement(service_id=booking_service.service_id)
    stored_file = make_stored_file("uploads/file.pdf")
    requirement_file = make_requirement_file(
        booking_service=booking_service,
        requirement=requirement,
        stored_file=stored_file,
    )
    booking_service.requirement_file_links = [requirement_file]
    booking.services = [booking_service]
    service = KpService(kp_repo, storage_service, staff_user)
    kp_repo.get_by_id.return_value = make_event(event_id=event_id)
    kp_repo.get_booking_by_id.return_value = booking

    result = await service.list_staff_booking_requirement_files(event_id, booking.id)

    assert list(result.files) == [requirement.id]
    assert result.files[requirement.id].stored_file.original_filename == "old.pdf"


async def test_list_staff_booking_requirement_files_rejects_event_mismatch(
    kp_repo,
    storage_service,
    staff_user,
):
    event_id = uuid4()
    booking = make_booking(event_id=uuid4())
    service = KpService(kp_repo, storage_service, staff_user)
    kp_repo.get_by_id.return_value = make_event(event_id=event_id)
    kp_repo.get_booking_by_id.return_value = booking

    with pytest.raises(KpBookingNotFound):
        await service.list_staff_booking_requirement_files(event_id, booking.id)


async def test_cleanup_orphaned_stored_files_deletes_storage_and_rows(kp_service):
    orphaned = [make_stored_file("orphan/one.pdf"), make_stored_file("orphan/two.pdf")]
    kp_service.kp_repo.list_orphaned_stored_files.return_value = orphaned

    await kp_service.service.cleanup_orphaned_stored_files()

    kp_service.storage_service.delete_object.assert_any_await("orphan/one.pdf")
    kp_service.storage_service.delete_object.assert_any_await("orphan/two.pdf")
    kp_service.kp_repo.delete_stored_file.assert_any_await(orphaned[0])
    kp_service.kp_repo.delete_stored_file.assert_any_await(orphaned[1])
