from typing import Any

import pytest

from app.core.config import (
    EXAMPLE_SECRET_KEY,
    MIN_SECRET_KEY_LENGTH,
    Settings,
    WeakSecretKey,
    get_settings,
)
from tests.conftest import EXAMPLE_ENV_FILE, read_env_file

STRONG_SECRET_KEY = "a" * MIN_SECRET_KEY_LENGTH


def _settings(**overrides: Any) -> Settings:
    return Settings.model_validate({**get_settings().model_dump(), **overrides})


def _settings_from_example_env() -> Settings:
    values = read_env_file(EXAMPLE_ENV_FILE)
    return Settings.model_validate(
        {key: value for key, value in values.items() if key in Settings.model_fields}
    )


def test_production_rejects_the_example_secret_key():
    with pytest.raises(WeakSecretKey):
        _settings(DEBUG=False, SECRET_KEY=EXAMPLE_SECRET_KEY)


def test_production_rejects_a_short_secret_key():
    with pytest.raises(WeakSecretKey):
        _settings(DEBUG=False, SECRET_KEY="a" * (MIN_SECRET_KEY_LENGTH - 1))


def test_production_accepts_a_strong_secret_key():
    assert _settings(DEBUG=False, SECRET_KEY=STRONG_SECRET_KEY).SECRET_KEY == (
        STRONG_SECRET_KEY
    )


def test_debug_accepts_the_example_secret_key():
    assert _settings(DEBUG=True, SECRET_KEY=EXAMPLE_SECRET_KEY).SECRET_KEY == (
        EXAMPLE_SECRET_KEY
    )


def test_the_example_env_file_is_accepted_as_is():
    settings = _settings_from_example_env()

    assert settings.DEBUG is True
    assert settings.SECRET_KEY == EXAMPLE_SECRET_KEY
