from typing import Any

import pytest

from app.core.config import (
    EXAMPLE_SECRET_KEY,
    MIN_SECRET_KEY_LENGTH,
    OAuthSettings,
    Settings,
    WeakSecretKey,
    get_oauth_settings,
    get_settings,
)
from tests.conftest import EXAMPLE_ENV_FILE, read_env_file

STRONG_SECRET_KEY = "a" * MIN_SECRET_KEY_LENGTH


def _settings(**overrides: Any) -> Settings:
    return Settings.model_validate({**get_settings().model_dump(), **overrides})


def _oauth_settings(**overrides: Any) -> OAuthSettings:
    return OAuthSettings.model_validate(
        {**get_oauth_settings().model_dump(), **overrides}
    )


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


def test_general_settings_load_without_application_credentials():
    assert _settings_from_example_env().DEBUG is True


def test_example_oauth_settings_require_application_credentials():
    values = read_env_file(EXAMPLE_ENV_FILE)
    with pytest.raises(ValueError, match="must not be empty"):
        OAuthSettings.model_validate(
            {key: values[key] for key in OAuthSettings.model_fields}
        )


@pytest.mark.parametrize(
    "name", ["SIP_AUTH_OIDC_CLIENT_ID", "SIP_AUTH_OIDC_CLIENT_SECRET"]
)
@pytest.mark.parametrize("value", ["", "   "])
def test_oauth_credentials_must_not_be_empty(name, value):
    with pytest.raises(ValueError, match="must not be empty"):
        _oauth_settings(**{name: value})


@pytest.mark.parametrize(
    "name",
    [
        "SIP_AUTH_OIDC_TOKEN_ENDPOINT",
        "SIP_AUTH_OIDC_CLIENT_ID",
        "SIP_AUTH_OIDC_CLIENT_SECRET",
    ],
)
def test_oauth_configuration_is_required(name, monkeypatch):
    values = get_oauth_settings().model_dump()
    values.pop(name)
    monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match=name):
        OAuthSettings.model_validate(values)


@pytest.mark.parametrize(
    "url",
    [
        "http://identity.example.org/token",
        "https://username:password@identity.example.org/token",
        "https://identity.example.org/token?secret=value",
        "https://identity.example.org/token#fragment",
    ],
)
def test_oauth_endpoint_must_be_https_without_embedded_credentials(url):
    with pytest.raises(ValueError, match="SIP_AUTH_OIDC_TOKEN_ENDPOINT must be HTTPS"):
        _oauth_settings(SIP_AUTH_OIDC_TOKEN_ENDPOINT=url)


def test_plaintext_notification_api_requires_explicit_configuration():
    assert Settings.model_fields["NOTIFICATION_API_TLS"].default is True
    assert _settings(NOTIFICATION_API_TLS=False).NOTIFICATION_API_TLS is False


def test_plaintext_notification_api_rejects_unused_ca_configuration():
    with pytest.raises(ValueError, match="NOTIFICATION_API_CA_FILE requires"):
        _settings(NOTIFICATION_API_TLS=False, NOTIFICATION_API_CA_FILE="ca.pem")


def test_configuration_errors_and_repr_hide_secret():
    secret = "do-not-show-this-oauth-secret"
    settings = _oauth_settings(SIP_AUTH_OIDC_CLIENT_SECRET=secret)
    assert secret not in repr(settings)
    with pytest.raises(ValueError) as error:
        _oauth_settings(SIP_AUTH_OIDC_CLIENT_SECRET=secret, SIP_AUTH_OIDC_CLIENT_ID="")
    assert secret not in str(error.value)


def test_service_account_reuses_browser_login_configuration():
    settings = _settings(
        SIP_AUTH_OIDC_CLIENT_ID="shared-client",
        SIP_AUTH_OIDC_CLIENT_SECRET="shared-secret",
        SIP_AUTH_OIDC_TOKEN_ENDPOINT="https://identity.example.org/shared/token",
    )
    oauth = OAuthSettings.from_settings(settings)
    assert oauth.SIP_AUTH_OIDC_CLIENT_ID == settings.SIP_AUTH_OIDC_CLIENT_ID
    assert oauth.SIP_AUTH_OIDC_CLIENT_SECRET == settings.SIP_AUTH_OIDC_CLIENT_SECRET
    assert (
        str(oauth.SIP_AUTH_OIDC_TOKEN_ENDPOINT) == settings.SIP_AUTH_OIDC_TOKEN_ENDPOINT
    )
    assert "shared-secret" not in repr(settings)
    assert "shared-secret" not in repr(oauth)
