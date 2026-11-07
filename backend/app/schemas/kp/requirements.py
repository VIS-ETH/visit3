from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.kp.files import StoredFileResponse
from app.schemas.text import REQUIREMENT_TEXT_MAX_LENGTH


class RequirementFileResponse(BaseModel):
    id: UUID
    booking_service_id: UUID
    requirement_id: UUID
    stored_file: StoredFileResponse


class RequirementTextRequest(BaseModel):
    text_value: str = Field(min_length=1, max_length=REQUIREMENT_TEXT_MAX_LENGTH)


class RequirementTextResponse(BaseModel):
    id: UUID
    booking_service_id: UUID
    requirement_id: UUID
    text_value: str


class RequirementFileDownloadResponse(BaseModel):
    url: str


class BookingRequirementFileMapResponse(BaseModel):
    files: dict[UUID, RequirementFileResponse]
