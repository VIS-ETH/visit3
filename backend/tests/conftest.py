import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
EXAMPLE_ENV_FILE = BACKEND_DIR / ".env.example"


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _load_test_env_defaults() -> None:
    env_file = ENV_FILE if ENV_FILE.exists() else EXAMPLE_ENV_FILE
    for key, value in read_env_file(env_file).items():
        os.environ.setdefault(key, value)


_load_test_env_defaults()
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-6d1b0a4f9c2e7a3b5d8f1c6e0a9b4d72"

from collections.abc import AsyncIterator, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import cookies
from app.core.config import Settings, get_settings
from tests.sqlite_db import sqlite_engine


@pytest.fixture
def debug_setting(monkeypatch: pytest.MonkeyPatch) -> Callable[[bool], None]:
    def _debug_setting(debug: bool) -> None:
        settings = Settings.model_validate(
            {**get_settings().model_dump(), "DEBUG": debug}
        )
        monkeypatch.setattr(cookies, "get_settings", lambda: settings)

    return _debug_setting


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with sqlite_engine() as engine:
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            yield session
