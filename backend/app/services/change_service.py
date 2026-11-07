from datetime import datetime, timedelta

from app.core.auth_context import require_staff_user
from app.core.dates import as_utc, utc_now
from app.models.kp_event import KpEvent, KpEventBooking
from app.models.user import User
from app.repositories.change_repository import ChangeRepository
from app.schemas.changes import (
    ChangedBookingResult,
    ChangedCompanyResult,
    ChangedEventResult,
    ChangedUserResult,
    RecentChangesResult,
)

FALLBACK_WINDOW = timedelta(days=7)
CHANGE_LIST_LIMIT = 50


def changes_since(user: User) -> datetime:
    seen = user.changes_seen_at or user.previous_login_at
    return as_utc(seen) if seen is not None else utc_now() - FALLBACK_WINDOW


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


def event_result(event: KpEvent) -> ChangedEventResult:
    return ChangedEventResult(id=event.id, name=event.name)


class ChangeService:
    def __init__(self, change_repository: ChangeRepository, current_user: User):
        self.change_repository = change_repository
        self.current_user = current_user

    async def recent_changes(self) -> RecentChangesResult:
        require_staff_user(self.current_user)
        as_of = utc_now()
        since = changes_since(self.current_user)
        users, users_total = await self.change_repository.new_users(
            since, CHANGE_LIST_LIMIT
        )
        companies, companies_total = await self.change_repository.new_companies(
            since, CHANGE_LIST_LIMIT
        )
        new_bookings, new_total, new_events = await self.change_repository.bookings(
            since, CHANGE_LIST_LIMIT, new=True
        )
        (
            changed_bookings,
            changed_total,
            changed_events,
        ) = await self.change_repository.bookings(since, CHANGE_LIST_LIMIT, new=False)
        return RecentChangesResult(
            since=since,
            as_of=as_of,
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
            new_booking_events=[event_result(event) for event in new_events],
            changed_bookings=[changed_booking_result(b) for b in changed_bookings],
            changed_bookings_total=changed_total,
            changed_booking_events=[event_result(event) for event in changed_events],
        )

    async def mark_changes_seen(self, as_of: datetime) -> None:
        require_staff_user(self.current_user)
        await self.change_repository.mark_changes_seen(
            self.current_user.id, min(as_utc(as_of), utc_now())
        )
