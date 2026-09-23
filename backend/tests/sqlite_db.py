from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from itertools import count
from typing import cast

from sqlalchemy import JSON, Dialect, TypeDecorator, event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.core.deleted_filter import hide_deleted_rows_in_orm_queries
from app.models.auth_tokens import LoginLinkToken
from app.models.company import (
    Company,
    CompanyInvite,
    KpCompanyLanguage,
    KpCompanyProfile,
)
from app.models.industry import Industry, KpCompanyProfileIndustryLink
from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpBookingCompanyDetailsIndustryLink,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventBoothZoneServiceLink,
    KpEventNametagBackground,
    KpEventRegistrationException,
    KpEventService,
    KpEventServiceRequirement,
    NameTag,
)
from app.models.mail import MailTemplate
from app.models.storage import StoredFile
from app.models.user import (
    ConfirmEmailToken,
    RefreshToken,
    ResetPasswordToken,
    Role,
    User,
    UserRole,
)
from app.models.venue import KpVenueBooth, KpVenueLayout, KpVenueZoneShape

hide_deleted_rows_in_orm_queries()


class CompanyLanguageArray(TypeDecorator[list[KpCompanyLanguage]]):
    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: list[KpCompanyLanguage] | None, dialect: Dialect
    ) -> list[str] | None:
        if value is None:
            return None
        return [KpCompanyLanguage(language).value for language in value]

    def process_result_value(
        self, value: list[str] | None, dialect: Dialect
    ) -> list[KpCompanyLanguage] | None:
        if value is None:
            return None
        return [KpCompanyLanguage(language) for language in value]


def _replace_postgres_array_with_json() -> None:
    KpBookingCompanyDetails.__table__.columns["languages"].type = CompanyLanguageArray()
    KpCompanyProfile.__table__.columns["languages"].type = CompanyLanguageArray()


_replace_postgres_array_with_json()

SQLITE_TABLES = [
    Company.__table__,
    User.__table__,
    Role.__table__,
    UserRole.__table__,
    RefreshToken.__table__,
    ResetPasswordToken.__table__,
    ConfirmEmailToken.__table__,
    LoginLinkToken.__table__,
    MailTemplate.__table__,
    CompanyInvite.__table__,
    KpCompanyProfile.__table__,
    Industry.__table__,
    KpCompanyProfileIndustryLink.__table__,
    KpEvent.__table__,
    KpEventBoothZone.__table__,
    KpEventService.__table__,
    KpEventBoothZoneServiceLink.__table__,
    KpEventServiceRequirement.__table__,
    KpEventBooking.__table__,
    KpEventBookingService.__table__,
    KpEventBookingServiceFileLink.__table__,
    KpEventBookingUpgradeWaitlist.__table__,
    KpEventNametagBackground.__table__,
    KpEventRegistrationException.__table__,
    KpBookingCompanyDetails.__table__,
    KpBookingCompanyDetailsIndustryLink.__table__,
    NameTag.__table__,
    StoredFile.__table__,
    KpVenueLayout.__table__,
    KpVenueZoneShape.__table__,
    KpVenueBooth.__table__,
]


_booking_numbers = count(1000)


@event.listens_for(KpEventBooking, "before_insert")
def _assign_booking_number(
    _mapper: object, _connection: object, target: object
) -> None:
    booking = cast(KpEventBooking, target)
    if booking.booking_number is None:
        booking.booking_number = next(_booking_numbers)


@asynccontextmanager
async def sqlite_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all, tables=SQLITE_TABLES)

    try:
        yield engine
    finally:
        await engine.dispose()
