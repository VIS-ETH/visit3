"""Helpers for uploading, attaching, and replacing stored files."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.models.storage import StoredFile
from app.repositories.kp_repository import KpRepository
from app.services.storage_service import StorageService

T = TypeVar("T")


async def upload_and_replace_attached_file(
    storage_service: StorageService,
    kp_repository: KpRepository,
    filename: str,
    content: bytes,
    content_type: str,
    storage_key: str,
    old_stored_file: StoredFile | None,
    attach: Callable[[StoredFile], Awaitable[T]],
) -> tuple[StoredFile, T]:
    """Upload content, persist a StoredFile row, attach it, then clean up the old file.

    If attaching fails the freshly uploaded object is deleted so it does not
    become orphaned. The old file is only removed after the new one has been
    successfully attached.
    """
    stored_object = await storage_service.upload_bytes(
        key=storage_key,
        content=content,
        filename=filename,
        content_type=content_type,
    )
    try:
        stored_file = await kp_repository.upsert_stored_file(
            storage_key=stored_object.key,
            original_filename=filename,
            mime_type=stored_object.mime_type,
            size_bytes=stored_object.size_bytes,
            sha256=stored_object.sha256,
            etag=stored_object.etag,
            stored_file=None,
        )
        attach_result = await attach(stored_file)
    except Exception:
        await storage_service.delete_object(stored_object.key)
        raise

    if old_stored_file is not None and old_stored_file.storage_key != stored_object.key:
        await storage_service.delete_object(old_stored_file.storage_key)
        await kp_repository.delete_stored_file(old_stored_file)

    return stored_file, attach_result


async def delete_attached_file(
    storage_service: StorageService,
    kp_repository: KpRepository,
    old_stored_file: StoredFile,
    detach: Callable[[], Awaitable[T]],
) -> T:
    """Detach a stored file from its parent and delete both object and row.

    Returns the value produced by ``detach`` so callers can use the updated
    parent record (e.g. a service row with its image reference cleared).
    """
    detach_result = await detach()
    await storage_service.delete_object(old_stored_file.storage_key)
    await kp_repository.delete_stored_file(old_stored_file)
    return detach_result
