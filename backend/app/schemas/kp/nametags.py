from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.kp_event import MAX_SERVICE_QUANTITY
from app.schemas.kp.files import StoredFileResponse
from app.schemas.text import NAME_MAX_LENGTH


class ExportBackgroundResponse(BaseModel):
    id: UUID
    event_id: UUID
    created_at: datetime
    updated_at: datetime
    stored_file: StoredFileResponse


class NameTagInput(BaseModel):
    first_name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    last_name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    position: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)


class ReplaceNameTagsInput(BaseModel):
    name_tags: list[NameTagInput] = Field(
        default_factory=lambda: [], max_length=MAX_SERVICE_QUANTITY
    )


class ReplaceNameTagsRequest(ReplaceNameTagsInput):
    pass


class NameTagResult(BaseModel):
    id: UUID
    booking_id: UUID
    first_name: str
    last_name: str
    position: str


class NameTagResponse(NameTagResult):
    pass


class NametagExportPersonResult(BaseModel):
    id: UUID
    booking_id: UUID
    company_name: str
    first_name: str
    last_name: str
    position: str


class NametagExportCompanyResult(BaseModel):
    booking_id: UUID
    company_id: UUID
    company_name: str
    booth_zone_name: str
    booth_nr: int | None
    nametag_count: int


class NametagExportTargetsResult(BaseModel):
    companies: list[NametagExportCompanyResult]
    people: list[NametagExportPersonResult]


class NametagExportTargetsResponse(NametagExportTargetsResult):
    pass


class NametagPreviewResult(BaseModel):
    png_base64: str


class NametagPreviewResponse(NametagPreviewResult):
    pass
