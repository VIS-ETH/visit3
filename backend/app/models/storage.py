from sqlmodel import Field

from app.models.base import BaseEntity


class StoredFile(BaseEntity, table=True):
    storage_key: str = Field(unique=True, index=True)
    original_filename: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64, index=True)
    etag: str | None = None
