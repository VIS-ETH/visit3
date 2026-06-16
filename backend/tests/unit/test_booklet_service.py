from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    KpBookingConfirmedReadonly,
    KpBookingNotFound,
    KpBookingNotOwned,
    KpBookletAssetInvalidType,
    KpBookletExportTaskNotFound,
    KpBookletExportTaskNotReady,
    KpEventNotFound,
)
from app.models.kp_event import (
    KpBookingStatus,
    KpEventBookletAssets,
    KpEventBookletExportTask,
    KpEventBookletExportTaskStatus,
)
from app.services.booklet_service import (
    ASSET_FIELD_NAMES,
    BookletService,
    RenderedBooklet,
    _to_asset_type,
)
from tests.unit.factories import make_stored_file


@dataclass
class BookletServiceHarness:
    service: BookletService
    kp_repo: AsyncMock
    storage_service: AsyncMock
    pdf_service: AsyncMock


@pytest.fixture
def booklet_service(kp_repo, storage_service, staff_user):
    return BookletServiceHarness(
        service=BookletService(kp_repo, storage_service, AsyncMock(), staff_user),
        kp_repo=kp_repo,
        storage_service=storage_service,
        pdf_service=AsyncMock(),
    )


def test_to_asset_type_accepts_known_values():
    assert _to_asset_type("intro_page") == "intro_page"
    assert _to_asset_type("blank_page") == "blank_page"
    assert _to_asset_type("missing_advertisement") == "missing_advertisement"


def test_to_asset_type_rejects_unknown_value():
    with pytest.raises(KpBookletAssetInvalidType):
        _to_asset_type("unknown")


def test_assets_field_names_mapping():
    assert ASSET_FIELD_NAMES["intro_page"] == "intro_page_stored_file_id"
    assert ASSET_FIELD_NAMES["blank_page"] == "blank_page_stored_file_id"


def test_stored_file_to_response_maps_fields(booklet_service):
    stored_file = make_stored_file(
        storage_key="key",
        original_filename="file.pdf",
        size_bytes=1024,
    )

    response = booklet_service.service._stored_file_to_response(stored_file)

    assert response.id == stored_file.id
    assert response.original_filename == "file.pdf"
    assert response.mime_type == "application/pdf"


def test_assets_to_response_returns_empty_when_none(booklet_service):
    event_id = uuid4()
    response = booklet_service.service._assets_to_response(event_id, None)

    assert response.event_id == event_id
    assert response.intro_page is None
    assert response.blank_page is None


def test_assets_to_response_maps_files(booklet_service):
    event_id = uuid4()
    stored_file = make_stored_file(
        storage_key="key",
        original_filename="intro.pdf",
        size_bytes=1024,
    )
    assets = MagicMock(spec=KpEventBookletAssets)
    assets.id = uuid4()
    assets.event_id = event_id
    assets.intro_page_stored_file = stored_file
    assets.blank_page_stored_file = None
    assets.missing_advertisement_stored_file = None

    response = booklet_service.service._assets_to_response(event_id, assets)

    assert response.intro_page is not None
    assert response.intro_page.original_filename == "intro.pdf"
    assert response.blank_page is None


def test_task_to_response_maps_fields(booklet_service):
    task = MagicMock(spec=KpEventBookletExportTask)
    task.id = uuid4()
    task.event_id = uuid4()
    task.status = KpEventBookletExportTaskStatus.PENDING
    task.error = None
    task.started_at = None
    task.finished_at = None
    task.created_at = datetime.now(timezone.utc)
    task.output_stored_file = None

    response = booklet_service.service._task_to_response(task)

    assert response.id == task.id
    assert response.status == KpEventBookletExportTaskStatus.PENDING


@pytest.mark.asyncio
async def test_get_assets_requires_event(booklet_service):
    event_id = uuid4()
    booklet_service.kp_repo.get_by_id.return_value = None

    with pytest.raises(KpEventNotFound):
        await booklet_service.service.get_assets(event_id)


@pytest.mark.asyncio
async def test_get_assets_returns_mapped_assets(booklet_service):
    event_id = uuid4()
    booklet_service.kp_repo.get_by_id.return_value = object()
    booklet_service.kp_repo.get_booklet_assets.return_value = None

    response = await booklet_service.service.get_assets(event_id)

    assert response.event_id == event_id
    booklet_service.kp_repo.get_booklet_assets.assert_awaited_once_with(event_id)


@pytest.mark.asyncio
async def test_delete_asset_returns_existing_when_no_file(booklet_service):
    event_id = uuid4()
    booklet_service.kp_repo.get_by_id.return_value = object()
    booklet_service.kp_repo.get_booklet_assets.return_value = None

    response = await booklet_service.service.delete_asset(event_id, "intro_page")

    assert response.event_id == event_id
    booklet_service.storage_service.delete_object.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_export_task_requires_event(booklet_service):
    event_id = uuid4()
    booklet_service.kp_repo.get_by_id.return_value = None

    with pytest.raises(KpEventNotFound):
        await booklet_service.service.create_export_task(event_id)


@pytest.mark.asyncio
async def test_create_export_task_returns_mapped_task(booklet_service):
    event_id = uuid4()
    task = MagicMock(spec=KpEventBookletExportTask)
    task.id = uuid4()
    task.event_id = event_id
    task.status = KpEventBookletExportTaskStatus.PENDING
    task.error = None
    task.started_at = None
    task.finished_at = None
    task.created_at = datetime.now(timezone.utc)
    task.output_stored_file = None
    booklet_service.kp_repo.get_by_id.return_value = object()
    booklet_service.kp_repo.create_booklet_export_task.return_value = task

    response = await booklet_service.service.create_export_task(event_id)

    assert response.id == task.id
    booklet_service.kp_repo.create_booklet_export_task.assert_awaited_once_with(
        event_id
    )


@pytest.mark.asyncio
async def test_get_export_task_raises_when_missing(booklet_service):
    booklet_service.kp_repo.get_booklet_export_task.return_value = None

    with pytest.raises(KpBookletExportTaskNotFound):
        await booklet_service.service.get_export_task(uuid4())


@pytest.mark.asyncio
async def test_get_export_task_download_url_raises_when_not_completed(
    booklet_service,
):
    task = MagicMock(spec=KpEventBookletExportTask)
    task.status = KpEventBookletExportTaskStatus.PENDING
    task.output_stored_file = None
    booklet_service.kp_repo.get_booklet_export_task.return_value = task

    with pytest.raises(KpBookletExportTaskNotReady):
        await booklet_service.service.get_export_task_download_url(uuid4())


@pytest.mark.asyncio
async def test_upload_company_logo_rejects_missing_booking(
    booklet_service,
    make_user,
):
    user = make_user(company_id=uuid4())
    service = BookletService(
        booklet_service.kp_repo,
        booklet_service.storage_service,
        AsyncMock(),
        user,
    )
    booklet_service.kp_repo.get_booking_by_id.return_value = None

    with pytest.raises(KpBookingNotFound):
        await service.upload_company_logo(
            uuid4(), "logo.png", b"content", "image/png"
        )


@pytest.mark.asyncio
async def test_upload_company_logo_rejects_not_owned_booking(
    booklet_service,
    make_user,
):
    user = make_user(company_id=uuid4())
    service = BookletService(
        booklet_service.kp_repo,
        booklet_service.storage_service,
        AsyncMock(),
        user,
    )
    booking = MagicMock()
    booking.company_id = uuid4()
    booking.status = KpBookingStatus.DRAFT
    booklet_service.kp_repo.get_booking_by_id.return_value = booking

    with pytest.raises(KpBookingNotOwned):
        await service.upload_company_logo(
            uuid4(), "logo.png", b"content", "image/png"
        )


@pytest.mark.asyncio
async def test_upload_company_logo_rejects_readonly_booking(
    booklet_service,
    make_user,
):
    user_company_id = uuid4()
    user = make_user(company_id=user_company_id)
    service = BookletService(
        booklet_service.kp_repo,
        booklet_service.storage_service,
        AsyncMock(),
        user,
    )
    booking = MagicMock()
    booking.company_id = user_company_id
    booking.status = KpBookingStatus.CONFIRMED
    booklet_service.kp_repo.get_booking_by_id.return_value = booking

    with pytest.raises(KpBookingConfirmedReadonly):
        await service.upload_company_logo(
            uuid4(), "logo.png", b"content", "image/png"
        )


@pytest.mark.asyncio
async def test_delete_company_logo_is_noop_when_no_details(
    booklet_service,
    make_user,
):
    user_company_id = uuid4()
    user = make_user(company_id=user_company_id)
    service = BookletService(
        booklet_service.kp_repo,
        booklet_service.storage_service,
        AsyncMock(),
        user,
    )
    booking = MagicMock()
    booking.company_id = user_company_id
    booking.status = KpBookingStatus.DRAFT
    booklet_service.kp_repo.get_booking_by_id.return_value = booking
    booklet_service.kp_repo.get_company_details_by_booking_id.return_value = None

    await service.delete_company_logo(uuid4())

    booklet_service.storage_service.delete_object.assert_not_awaited()


@pytest.mark.asyncio
async def test_store_rendered_booklet_uploads_and_completes_task(
    booklet_service,
):
    task = MagicMock(spec=KpEventBookletExportTask)
    task.id = uuid4()
    task.event_id = uuid4()
    stored_object = MagicMock()
    stored_object.key = "storage-key"
    stored_object.mime_type = "application/pdf"
    stored_object.size_bytes = 1024
    stored_object.sha256 = "sha256"
    stored_object.etag = "etag"
    booklet_service.storage_service.upload_bytes.return_value = stored_object
    stored_file = make_stored_file(
        storage_key="storage-key",
        original_filename="booklet.pdf",
        size_bytes=1024,
    )
    booklet_service.kp_repo.upsert_stored_file.return_value = stored_file
    completed_task = MagicMock(spec=KpEventBookletExportTask)
    booklet_service.kp_repo.complete_booklet_export_task.return_value = completed_task

    rendered = RenderedBooklet(content=b"pdf", filename="booklet.pdf")
    result = await booklet_service.service.store_rendered_booklet(task, rendered)

    assert result is completed_task
    booklet_service.storage_service.upload_bytes.assert_awaited_once()
    booklet_service.kp_repo.complete_booklet_export_task.assert_awaited_once_with(
        task, stored_file.id
    )
