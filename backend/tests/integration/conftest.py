from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.company_repository import CompanyRepository
from app.repositories.industry_repository import IndustryRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.mail_repository import MailTemplateRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.venue_repository import VenueRepository
from app.services.auth_service import AuthService
from app.services.invite_service import InviteService
from app.services.mail_template_service import MailTemplateService


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
def industry_repository(db_session: AsyncSession) -> IndustryRepository:
    return IndustryRepository(db_session)


@pytest.fixture
def kp_repository(db_session: AsyncSession) -> KpRepository:
    return KpRepository(db_session)


@pytest.fixture
def mail_template_repository(db_session: AsyncSession) -> MailTemplateRepository:
    return MailTemplateRepository(db_session)


@pytest.fixture
def venue_repository(db_session: AsyncSession) -> VenueRepository:
    return VenueRepository(db_session)


@pytest.fixture
def mail_template_service() -> AsyncMock:
    return AsyncMock(spec=MailTemplateService)


@pytest.fixture
def invite_service(company_repository: CompanyRepository) -> InviteService:
    return InviteService(company_repository)


@pytest.fixture
def auth_service(
    user_repository: UserRepository,
    token_repository: TokenRepository,
    role_repository: RoleRepository,
    mail_template_service: AsyncMock,
    invite_service: InviteService,
) -> AuthService:
    return AuthService(
        user_repository,
        token_repository,
        role_repository,
        mail_template_service,
        invite_service,
    )
