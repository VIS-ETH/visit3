from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage import StoredFile


class StoredFileQueries:
    session: AsyncSession
    committing: Callable[[], AbstractAsyncContextManager[None]]

    async def create_stored_file(
        self,
        *,
        storage_key: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        etag: str | None,
    ) -> StoredFile:
        stored_file = StoredFile(
            storage_key=storage_key,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            etag=etag,
        )
        async with self.committing():
            self.session.add(stored_file)
        await self.session.refresh(stored_file)
        return stored_file

    async def get_stored_file(self, stored_file_id: UUID) -> Optional[StoredFile]:
        return await self.session.get(StoredFile, stored_file_id)

    async def delete_stored_file(self, stored_file: StoredFile) -> None:
        async with self.committing():
            await self.session.delete(stored_file)
