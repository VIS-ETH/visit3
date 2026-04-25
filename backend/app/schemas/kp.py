from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
)


class CreateKpRequest(BaseModel):
    name: str
    registration_open: date
    registration_end: date
    finalization_deadline: date
    nametags_deadline: date
    event_date: date


class KpResponse(BaseModel):
    id: UUID
    name: str
    registration_open: date
    registration_end: date
    finalization_deadline: date
    nametags_deadline: date
    event_date: date

    @classmethod
    def from_model(cls, event: KpEvent) -> "KpResponse":
        return cls(
            id=event.id,
            name=event.name,
            registration_open=event.registration_open,
            registration_end=event.registration_end,
            finalization_deadline=event.finalization_deadline,
            nametags_deadline=event.nametags_deadline,
            event_date=event.event_date,
        )


class ReplaceBookingUpgradeWaitlistRequest(BaseModel):
    target_booth_zone_ids: list[UUID]


class BookingResponse(BaseModel):
    id: UUID
    event_id: UUID
    company_id: UUID
    booth_zone_id: UUID
    booth_nr: int
    status: KpBookingStatus

    @classmethod
    def from_model(cls, booking: KpEventBooking) -> "BookingResponse":
        return cls(
            id=booking.id,
            event_id=booking.event_id,
            company_id=booking.company_id,
            booth_zone_id=booking.booth_zone_id,
            booth_nr=booking.booth_nr,
            status=booking.status,
        )


class UpdateBookingStatusRequest(BaseModel):
    status: KpBookingStatus


class UpdateBookingBoothNumberRequest(BaseModel):
    booth_nr: int = Field(ge=1)


class RequirementFileResponse(BaseModel):
    id: UUID
    booking_service_id: UUID
    requirement_id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    etag: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(
        cls, file: KpEventBookingServiceFileLink
    ) -> "RequirementFileResponse":
        return cls(
            id=file.stored_file.id,
            booking_service_id=file.booking_service_id,
            requirement_id=file.requirement_id,
            original_filename=file.stored_file.original_filename,
            mime_type=file.stored_file.mime_type,
            size_bytes=file.stored_file.size_bytes,
            sha256=file.stored_file.sha256,
            etag=file.stored_file.etag,
            created_at=file.stored_file.created_at,
            updated_at=file.stored_file.updated_at,
        )


class RequirementFileDownloadResponse(BaseModel):
    url: str


class BookingUpgradeWaitlistEntryResponse(BaseModel):
    id: UUID
    booking_id: UUID
    target_booth_zone_id: UUID
    target_booth_zone_name: str
    priority_rank: int | None

    @classmethod
    def from_model(
        cls, entry: KpEventBookingUpgradeWaitlist
    ) -> "BookingUpgradeWaitlistEntryResponse":
        return cls(
            id=entry.id,
            booking_id=entry.booking_id,
            target_booth_zone_id=entry.target_booth_zone_id,
            target_booth_zone_name=entry.target_booth_zone.name,
            priority_rank=entry.priority_rank,
        )
