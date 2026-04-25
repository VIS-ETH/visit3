from datetime import date
from uuid import UUID

from pydantic import BaseModel


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


class ReplaceBookingUpgradeWaitlistRequest(BaseModel):
    target_booth_zone_ids: list[UUID]


class BookingUpgradeWaitlistEntryResponse(BaseModel):
    id: UUID
    booking_id: UUID
    target_booth_zone_id: UUID
    target_booth_zone_name: str
    priority_rank: int | None
