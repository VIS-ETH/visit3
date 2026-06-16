from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.attachment_utils import (
    delete_attached_file,
    upload_and_replace_attached_file,
)
from app.services.storage_service import StoredObject


@pytest.fixture
def stored_object():
    return StoredObject(
        key=f"kp/events/{uuid4()}/file.pdf",
        etag="etag",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="sha256",
    )


@pytest.fixture
def old_stored_file():
    file = MagicMock()
    file.id = uuid4()
    file.storage_key = "old-key"
    return file


@pytest.fixture
def new_stored_file():
    file = MagicMock()
    file.id = uuid4()
    file.storage_key = "new-key"
    return file


@pytest.mark.asyncio
async def test_upload_and_replace_attached_file_cleans_up_old_file(
    storage_service, kp_repo, stored_object, old_stored_file, new_stored_file
):
    storage_service.upload_bytes.return_value = stored_object
    kp_repo.upsert_stored_file.return_value = new_stored_file
    attach = AsyncMock(return_value="attached")

    result_file, result_attach = await upload_and_replace_attached_file(
        storage_service=storage_service,
        kp_repository=kp_repo,
        filename="file.pdf",
        content=b"content",
        content_type="application/pdf",
        storage_key=stored_object.key,
        old_stored_file=old_stored_file,
        attach=attach,
    )

    assert result_file is new_stored_file
    assert result_attach == "attached"
    storage_service.upload_bytes.assert_awaited_once()
    kp_repo.upsert_stored_file.assert_awaited_once()
    attach.assert_awaited_once_with(new_stored_file)
    storage_service.delete_object.assert_awaited_once_with(old_stored_file.storage_key)
    kp_repo.delete_stored_file.assert_awaited_once_with(old_stored_file)


@pytest.mark.asyncio
async def test_upload_and_replace_attached_file_skips_old_cleanup_when_same_key(
    storage_service, kp_repo, stored_object, new_stored_file
):
    stored_object.key = "same-key"
    old_stored_file = MagicMock()
    old_stored_file.storage_key = "same-key"
    storage_service.upload_bytes.return_value = stored_object
    kp_repo.upsert_stored_file.return_value = new_stored_file

    await upload_and_replace_attached_file(
        storage_service=storage_service,
        kp_repository=kp_repo,
        filename="file.pdf",
        content=b"content",
        content_type="application/pdf",
        storage_key=stored_object.key,
        old_stored_file=old_stored_file,
        attach=AsyncMock(),
    )

    storage_service.delete_object.assert_not_awaited()
    kp_repo.delete_stored_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_and_replace_attached_file_deletes_new_object_on_attach_failure(
    storage_service, kp_repo, stored_object, new_stored_file
):
    storage_service.upload_bytes.return_value = stored_object
    kp_repo.upsert_stored_file.return_value = new_stored_file
    attach = AsyncMock(side_effect=RuntimeError("attach failed"))

    with pytest.raises(RuntimeError, match="attach failed"):
        await upload_and_replace_attached_file(
            storage_service=storage_service,
            kp_repository=kp_repo,
            filename="file.pdf",
            content=b"content",
            content_type="application/pdf",
            storage_key=stored_object.key,
            old_stored_file=None,
            attach=attach,
        )

    storage_service.delete_object.assert_awaited_once_with(stored_object.key)


@pytest.mark.asyncio
async def test_upload_and_replace_attached_file_no_old_file(
    storage_service, kp_repo, stored_object, new_stored_file
):
    storage_service.upload_bytes.return_value = stored_object
    kp_repo.upsert_stored_file.return_value = new_stored_file

    await upload_and_replace_attached_file(
        storage_service=storage_service,
        kp_repository=kp_repo,
        filename="file.pdf",
        content=b"content",
        content_type="application/pdf",
        storage_key=stored_object.key,
        old_stored_file=None,
        attach=AsyncMock(),
    )

    storage_service.delete_object.assert_not_awaited()
    kp_repo.delete_stored_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_attached_file_deletes_object_and_row(
    storage_service, kp_repo, old_stored_file
):
    detach = AsyncMock(return_value="detached")

    result = await delete_attached_file(
        storage_service=storage_service,
        kp_repository=kp_repo,
        old_stored_file=old_stored_file,
        detach=detach,
    )

    assert result == "detached"
    detach.assert_awaited_once()
    storage_service.delete_object.assert_awaited_once_with(old_stored_file.storage_key)
    kp_repo.delete_stored_file.assert_awaited_once_with(old_stored_file)
