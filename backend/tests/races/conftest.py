import asyncio
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import deps
from app.core.config import get_settings
from app.main import app as fastapi_app
from app.models.company import KpCompanyProfile, company_language_column
from app.models.kp_event import KpBookingCompanyDetails
from tests.api.conftest import (  # noqa: F401
    admin_headers,
    admin_user,
    auth_headers,
    auth_service,
    clear_rate_limits,
    client,
    company_headers,
    company_user,
    complete_company_profile,
    create_user,
    csrf_headers,
    kp_setup,
    mail_stub,
    mail_template_service,
    president_headers,
    president_user,
    register_booking,
    staff_headers,
    staff_user,
    storage_service,
)

POSTGRES_URL = os.environ.get("TEST_POSTGRES_URL")
RACES_DIR = Path(__file__).parent
KEPT_TABLES = ("alembic_version", "mailtemplate")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if POSTGRES_URL:
        return
    skip = pytest.mark.skip(reason="TEST_POSTGRES_URL is not set")
    for item in items:
        if item.path.is_relative_to(RACES_DIR):
            item.add_marker(skip)


@pytest.fixture
async def pg_sessionmaker(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert POSTGRES_URL is not None
    for model in (KpCompanyProfile, KpBookingCompanyDetails):
        column = model.__table__.columns["languages"]
        monkeypatch.setattr(column, "type", company_language_column().type)
    engine = create_async_engine(POSTGRES_URL, pool_size=20, max_overflow=20)
    async with engine.begin() as connection:
        tables = (
            await connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename <> ALL(:kept)"
                ),
                {"kept": list(KEPT_TABLES)},
            )
        ).scalars()
        await connection.execute(
            text("TRUNCATE " + ", ".join(f'"{table}"' for table in tables) + " CASCADE")
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def db_session(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with pg_sessionmaker() as session:
        yield session


@pytest.fixture
def api_app(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
    mail_stub: AsyncMock,  # noqa: F811
    storage_service: AsyncMock,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[FastAPI]:
    monkeypatch.setattr(get_settings(), "MAIL_CAMPAIGN_SEND_PAUSE_SECONDS", 0)

    async def own_session() -> AsyncIterator[AsyncSession]:
        async with pg_sessionmaker() as session:
            yield session

    async def stub() -> AsyncMock:
        return mail_stub

    fastapi_app.dependency_overrides[deps.get_db_session] = own_session
    fastapi_app.dependency_overrides[deps.get_stub] = stub
    fastapi_app.dependency_overrides[deps.get_storage_service] = lambda: storage_service
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def slow_down(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[..., None]:
    def _slow_down(
        owner: object, name: str, seconds: float, *, before: bool = False
    ) -> None:
        original: Callable[..., Awaitable[Any]] = getattr(owner, name)

        async def slowed(*args: Any, **kwargs: Any) -> Any:
            if before:
                await asyncio.sleep(seconds)
            result = await original(*args, **kwargs)
            if not before:
                await asyncio.sleep(seconds)
            return result

        monkeypatch.setattr(owner, name, slowed)

    return _slow_down
