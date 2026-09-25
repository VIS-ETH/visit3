from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import grpc as grpc_module
from app.core.config import OAuthSettings, Settings, get_settings
from app.core.service_account import OAuthTokenError


@pytest.fixture
def connection(monkeypatch):
    channel = MagicMock()
    channel.channel_ready = AsyncMock()
    channel.close = AsyncMock()
    source = AsyncMock()
    factory = MagicMock(return_value=source)
    secure_channel = MagicMock(return_value=channel)
    insecure_channel = MagicMock()
    ssl_credentials = MagicMock()
    monkeypatch.setattr(grpc_module, "ServiceAccountCredential", factory)
    monkeypatch.setattr(grpc_module.grpc.aio, "secure_channel", secure_channel)
    monkeypatch.setattr(grpc_module.grpc.aio, "insecure_channel", insecure_channel)
    monkeypatch.setattr(grpc_module.grpc, "ssl_channel_credentials", ssl_credentials)
    return channel, source, secure_channel, insecure_channel, ssl_credentials


async def test_connect_authenticates_before_opening_verified_tls_channel(connection):
    channel, source, secure_channel, insecure_channel, ssl_credentials = connection

    def check_start(*args, **kwargs):
        source.start.assert_awaited_once()
        return channel

    secure_channel.side_effect = check_start
    client = grpc_module.GRPCClient()
    await client.connect("notifications.example.org:443")
    insecure_channel.assert_not_called()
    ssl_credentials.assert_called_once_with(root_certificates=None)
    call = secure_channel.call_args
    assert call.args == ("notifications.example.org:443", ssl_credentials.return_value)
    assert set(call.kwargs) == {"interceptors"}  # No TLS hostname override/options.
    assert call.kwargs["interceptors"][0].credentials is source
    assert client.stub is not None
    await client.disconnect()
    channel.close.assert_awaited_once()
    source.close.assert_awaited_once()
    assert client.channel is client.stub is client.credentials is None


async def test_custom_ca_keeps_verified_tls(connection, monkeypatch, tmp_path):
    _, _, _, _, ssl_credentials = connection
    ca = tmp_path / "ca.pem"
    ca.write_bytes(b"test-ca-certificate")
    settings = get_settings().model_copy(update={"NOTIFICATION_API_CA_FILE": str(ca)})
    monkeypatch.setattr(grpc_module, "get_settings", lambda: settings)
    client = grpc_module.GRPCClient()
    await client.connect("notifications.example.org:443")
    ssl_credentials.assert_called_once_with(root_certificates=b"test-ca-certificate")
    await client.disconnect()


async def test_startup_token_failure_closes_source_and_never_opens_channel(connection):
    _, source, secure_channel, _, _ = connection
    source.start.side_effect = OAuthTokenError("obtain OAuth access token: HTTP 401")
    client = grpc_module.GRPCClient()
    with pytest.raises(OAuthTokenError, match="HTTP 401"):
        await client.connect("notifications.example.org:443")
    secure_channel.assert_not_called()
    source.close.assert_awaited_once()
    assert client.stub is None


async def test_channel_failure_closes_both_clients(connection):
    channel, source, _, _, _ = connection
    channel.channel_ready.side_effect = TimeoutError()
    client = grpc_module.GRPCClient()
    with pytest.raises(RuntimeError, match="connection timed out"):
        await client.connect("notifications.example.org:443")
    channel.close.assert_awaited_once()
    source.close.assert_awaited_once()
    assert client.stub is None


async def test_plaintext_channel_is_rejected(connection, monkeypatch):
    _, source, secure_channel, insecure_channel, _ = connection
    settings = get_settings().model_copy(update={"NOTIFICATION_API_TLS": False})
    monkeypatch.setattr(grpc_module, "get_settings", lambda: settings)
    client = grpc_module.GRPCClient()
    with pytest.raises(RuntimeError, match="requires TLS"):
        await client.connect("notifications.example.org:443")
    secure_channel.assert_not_called()
    insecure_channel.assert_not_called()
    source.close.assert_awaited_once()


@pytest.mark.parametrize(
    "name",
    [
        "SIP_AUTH_OIDC_TOKEN_ENDPOINT",
        "SIP_AUTH_OIDC_CLIENT_ID",
        "SIP_AUTH_OIDC_CLIENT_SECRET",
    ],
)
async def test_missing_oauth_config_fails_startup_before_creating_clients(
    connection, monkeypatch, name
):
    _, _, secure_channel, _, _ = connection
    monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        grpc_module,
        "get_oauth_settings",
        lambda: OAuthSettings.from_settings(Settings.from_environment()),
    )
    client = grpc_module.GRPCClient()
    with pytest.raises(ValueError, match=name):
        await client.connect("notifications.example.org:443")
    grpc_module.ServiceAccountCredential.assert_not_called()
    secure_channel.assert_not_called()
