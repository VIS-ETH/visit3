from datetime import datetime, timedelta, timezone

from app.core.auth_context import require_staff_user
from app.models.kp_event import KpEventBooking
from app.models.user import User
from app.repositories.change_repository import ChangeRepository
from app.schemas.changes import (
    ChangedBookingResult,
    ChangedCompanyResult,
    ChangedUserResult,
    RecentChangesResult,
)

FALLBACK_WINDOW = timedelta(days=7)
CHANGE_LIST_LIMIT = 50


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def changes_since(user: User) -> datetime:
    seen = user.changes_seen_at or user.previous_login_at
    return (
        as_utc(seen)
        if seen is not None
        else datetime.now(timezone.utc) - FALLBACK_WINDOW
    )


def booking_changed_at(booking: KpEventBooking) -> datetime:
    return max(
        [
            as_utc(booking.updated_at),
            *(as_utc(service.updated_at) for service in booking.services),
        ]
    )


def changed_booking_result(booking: KpEventBooking) -> ChangedBookingResult:
    return ChangedBookingResult(
        id=booking.id,
        event_id=booking.event_id,
        event_name=booking.event.name,
        company_id=booking.company_id,
        company_name=booking.company.name,
        booth_zone_name=booking.booth_zone.name,
        status=booking.status,
        created_at=booking.created_at,
        changed_at=booking_changed_at(booking),
    )


class ChangeService:
    def __init__(self, change_repository: ChangeRepository, current_user: User):
        self.change_repository = change_repository
        self.current_user = current_user

    async def recent_changes(self) -> RecentChangesResult:
        require_staff_user(self.current_user)
        since = changes_since(self.current_user)
        users, users_total = await self.change_repository.new_users(
            since, CHANGE_LIST_LIMIT
        )
        companies, companies_total = await self.change_repository.new_companies(
            since, CHANGE_LIST_LIMIT
        )
        new_bookings, new_total = await self.change_repository.bookings(
            since, CHANGE_LIST_LIMIT, new=True
        )
        changed_bookings, changed_total = await self.change_repository.bookings(
            since, CHANGE_LIST_LIMIT, new=False
        )
        return RecentChangesResult(
            since=since,
            new_users=[
                ChangedUserResult(
                    id=user.id,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    company_name=user.company.name if user.company else None,
                    created_at=user.created_at,
                )
                for user in users
            ],
            new_users_total=users_total,
            new_companies=[
                ChangedCompanyResult(
                    id=company.id,
                    name=company.name,
                    confirmed_at=company.confirmed_at,
                    created_at=company.created_at,
                )
                for company in companies
            ],
            new_companies_total=companies_total,
            new_bookings=[changed_booking_result(b) for b in new_bookings],
            new_bookings_total=new_total,
            changed_bookings=[changed_booking_result(b) for b in changed_bookings],
            changed_bookings_total=changed_total,
        )

    async def mark_changes_seen(self) -> None:
        require_staff_user(self.current_user)
        await self.change_repository.mark_changes_seen(
            self.current_user.id, datetime.now(timezone.utc)
        )
