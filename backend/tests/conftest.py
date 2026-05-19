import os
from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def _load_test_env_defaults() -> None:
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


_load_test_env_defaults()
os.environ["DEBUG"] = "false"

from app.models.company import Company
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.mail_service import MailService
from app.services.storage_service import StorageService


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def token_repo() -> AsyncMock:
    return AsyncMock(spec=TokenRepository)


@pytest.fixture
def role_repo() -> AsyncMock:
    return AsyncMock(spec=RoleRepository)


@pytest.fixture
def company_repo() -> AsyncMock:
    return AsyncMock(spec=CompanyRepository)


@pytest.fixture
def kp_repo() -> AsyncMock:
    return AsyncMock(spec=KpRepository)


@pytest.fixture
def mail_service() -> AsyncMock:
    return AsyncMock(spec=MailService)


@pytest.fixture
def storage_service() -> AsyncMock:
    return AsyncMock(spec=StorageService)


@pytest.fixture
def make_user() -> Callable[..., User]:
    def _make_user(
        *,
        email: str = "user@example.com",
        password: str | None = "password-hash",
        is_staff: bool = False,
        is_admin: bool = False,
        is_company: bool = True,
        user_confirmed: bool = True,
        email_confirmed: bool = True,
        company_id=None,
    ) -> User:
        return User(
            id=uuid4(),
            email=email,
            password=password,
            is_staff=is_staff,
            is_admin=is_admin,
            is_company=is_company,
            user_confirmed=user_confirmed,
            email_confirmed=email_confirmed,
            company_id=company_id,
        )

    return _make_user


@pytest.fixture
def make_company() -> Callable[..., Company]:
    def _make_company(*, name: str = "Acme AG") -> Company:
        return Company(id=uuid4(), name=name)

    return _make_company


@pytest.fixture
def company_user(make_user: Callable[..., User]) -> User:
    return make_user()


@pytest.fixture
def staff_user(make_user: Callable[..., User]) -> User:
    return make_user(
        email="staff@example.com",
        is_staff=True,
        is_company=False,
    )


@pytest.fixture
def admin_user(make_user: Callable[..., User]) -> User:
    return make_user(
        email="admin@example.com",
        is_staff=True,
        is_admin=True,
        is_company=False,
    )


@pytest.fixture
def unconfirmed_user(make_user: Callable[..., User]) -> User:
    return make_user(
        email="unconfirmed@example.com",
        user_confirmed=False,
        email_confirmed=False,
    )
