from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.kp_event import KpBookingStatus


class ChangedUserResult(BaseModel):
    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    created_at: datetime


class ChangedCompanyResult(BaseModel):
    id: UUID
    name: str
    confirmed_at: datetime | None
    created_at: datetime


class ChangedBookingResult(BaseModel):
    id: UUID
    event_id: UUID
    event_name: str
    company_id: UUID
    company_name: str
    booth_zone_name: str
    status: KpBookingStatus
    created_at: datetime
    changed_at: datetime


class RecentChangesResult(BaseModel):
    since: datetime
    new_users: list[ChangedUserResult]
    new_users_total: int
    new_companies: list[ChangedCompanyResult]
    new_companies_total: int
    new_bookings: list[ChangedBookingResult]
    new_bookings_total: int
    changed_bookings: list[ChangedBookingResult]
    changed_bookings_total: int


class RecentChangesResponse(RecentChangesResult):
    pass
