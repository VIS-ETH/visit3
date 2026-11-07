from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StoredFileResponse(BaseModel):
    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    etag: str | None
    created_at: datetime
    updated_at: datetime
