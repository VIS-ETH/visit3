import logging
from collections.abc import Awaitable, Callable
from typing import Optional, Protocol, TypeVar
from uuid import UUID, uuid4

from app.core.utils import bounded_filename, safe_suffix
from app.models.storage import StoredFile
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

AttachedT = TypeVar("AttachedT")


class StoredFileStore(Protocol):
    async def create_stored_file(
        self,
        *,
        storage_key: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        etag: str | None,
    ) -> StoredFile: ...

    async def get_stored_file(self, stored_file_id: UUID) -> Optional[StoredFile]: ...

    async def delete_stored_file(self, stored_file: StoredFile) -> None: ...


class StoredFiles:
    def __init__(self, storage_service: StorageService, store: StoredFileStore):
        self.storage_service = storage_service
        self.store = store

    async def save(
        self,
        prefix: str,
        filename: str,
        content: bytes,
        mime_type: str,
        attach: Callable[[StoredFile], Awaitable[AttachedT]],
        suffix: str | None = None,
    ) -> AttachedT:
        suffix = safe_suffix(filename) if suffix is None else suffix
        stored_object = await self.storage_service.upload_bytes(
            key=f"{prefix}/{uuid4()}{suffix}",
            content=content,
            filename=filename,
            content_type=mime_type,
        )
        try:
            stored_file = await self.store.create_stored_file(
                storage_key=stored_object.key,
                original_filename=bounded_filename(filename),
                mime_type=stored_object.mime_type,
                size_bytes=stored_object.size_bytes,
                sha256=stored_object.sha256,
                etag=stored_object.etag,
            )
            return await attach(stored_file)
        except BaseException:
            await self._delete_object(stored_object.key)
            raise

    async def discard(self, stored_file: StoredFile | None) -> None:
        if stored_file is None:
            return
        if await self._delete_object(stored_file.storage_key):
            await self.store.delete_stored_file(stored_file)

    async def _delete_object(self, key: str) -> bool:
        try:
            await self.storage_service.delete_object(key)
        except Exception:
            logger.warning("Stored object %s left for the orphan cleanup", key)
            return False
        return True
