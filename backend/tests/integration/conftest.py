from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.core.deleted_filter import register_deleted_filter
from app.models.company import Company, CompanyInvite, KpCompanyProfile
from app.models.kp_event import (
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
    KpIndustry,
    NameTag,
)
from app.models.storage import StoredFile
from app.models.user import (
    ConfirmEmailToken,
    ForgetPasswordToken,
    RefreshToken,
    Role,
    User,
    UserRole,
)
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository

register_deleted_filter()

INTEGRATION_TABLES = [
    Company.__table__,
    User.__table__,
    Role.__table__,
    UserRole.__table__,
    RefreshToken.__table__,
    ForgetPasswordToken.__table__,
    ConfirmEmailToken.__table__,
    CompanyInvite.__table__,
    KpCompanyProfile.__table__,
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
    KpIndustry.__table__,
    NameTag.__table__,
    StoredFile.__table__,
]


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as connection:
        await connection.run_sync(
            SQLModel.metadata.create_all,
            tables=INTEGRATION_TABLES,
        )

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def user_repository(db_session: AsyncSession) -> UserRepository:
    return UserRepository(db_session)


@pytest.fixture
def token_repository(db_session: AsyncSession) -> TokenRepository:
    return TokenRepository(db_session)


@pytest.fixture
def company_repository(db_session: AsyncSession) -> CompanyRepository:
    return CompanyRepository(db_session)


@pytest.fixture
def role_repository(db_session: AsyncSession) -> RoleRepository:
    return RoleRepository(db_session)


@pytest.fixture
def kp_repository(db_session: AsyncSession) -> KpRepository:
    return KpRepository(db_session)
