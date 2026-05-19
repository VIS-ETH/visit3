from dataclasses import dataclass
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    KpBookingAlreadyExists,
    KpBookingConfirmationRequiresFinalized,
    KpBookingStatusTransitionInvalid,
    KpBoothZoneAtCapacity,
    KpBoothZoneEventMismatch,
    KpNameExists,
    KpRegistrationClosed,
    KpRequirementFileUploadNotAllowed,
    KpServiceRequirementNotFound,
    KpWaitlistSameZone,
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
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
)
from app.models.storage import StoredFile
from app.schemas.kp import (
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

    assert result is booking
    kp_repo.create_booking.assert_awaited_once()
    kwargs = kp_repo.create_booking.await_args.kwargs
    assert kwargs["event_id"] == event.id
    assert kwargs["company_id"] == company_id
    assert kwargs["booth_zone_id"] == zone.id
    assert kwargs["create_booking_input"].status == KpBookingStatus.REGISTERED


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

    assert result is booking
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


async def test_cleanup_orphaned_stored_files_deletes_storage_and_rows(kp_service):
    orphaned = [make_stored_file("orphan/one.pdf"), make_stored_file("orphan/two.pdf")]
    kp_service.kp_repo.list_orphaned_stored_files.return_value = orphaned

    await kp_service.service.cleanup_orphaned_stored_files()

    kp_service.storage_service.delete_object.assert_any_await("orphan/one.pdf")
    kp_service.storage_service.delete_object.assert_any_await("orphan/two.pdf")
    kp_service.kp_repo.delete_stored_file.assert_any_await(orphaned[0])
    kp_service.kp_repo.delete_stored_file.assert_any_await(orphaned[1])
