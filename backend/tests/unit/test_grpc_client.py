from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import grpc as grpc_module
from app.core.config import Settings, get_settings


def _settings(**overrides: object) -> Settings:
    return get_settings().model_copy(update=overrides)


@pytest.fixture
def channel() -> MagicMock:
    channel = MagicMock()
    channel.channel_ready = AsyncMock()
    return channel


async def test_connect_uses_an_insecure_channel_by_default(
    monkeypatch: pytest.MonkeyPatch, channel: MagicMock
):
    insecure_channel = MagicMock(return_value=channel)
    secure_channel = MagicMock()
    monkeypatch.setattr(
        grpc_module, "get_settings", lambda: _settings(NOTIFICATION_API_TLS=False)
    )
    monkeypatch.setattr(grpc_module.grpc.aio, "insecure_channel", insecure_channel)
    monkeypatch.setattr(grpc_module.grpc.aio, "secure_channel", secure_channel)

    client = grpc_module.GRPCClient()
    await client.connect("notifications:6781")

    insecure_channel.assert_called_once_with("notifications:6781")
    secure_channel.assert_not_called()


async def test_connect_uses_a_secure_channel_when_tls_is_enabled(
    monkeypatch: pytest.MonkeyPatch, channel: MagicMock
):
    insecure_channel = MagicMock()
    secure_channel = MagicMock(return_value=channel)
    credentials = MagicMock()
    ssl_channel_credentials = MagicMock(return_value=credentials)
    monkeypatch.setattr(
        grpc_module, "get_settings", lambda: _settings(NOTIFICATION_API_TLS=True)
    )
    monkeypatch.setattr(grpc_module.grpc.aio, "insecure_channel", insecure_channel)
    monkeypatch.setattr(grpc_module.grpc.aio, "secure_channel", secure_channel)
    monkeypatch.setattr(
        grpc_module.grpc, "ssl_channel_credentials", ssl_channel_credentials
    )

    client = grpc_module.GRPCClient()
    await client.connect("notifications:6781")

    insecure_channel.assert_not_called()
    ssl_channel_credentials.assert_called_once_with(root_certificates=None)
    secure_channel.assert_called_once_with("notifications:6781", credentials)


async def test_connect_reads_the_configured_ca_certificate(
    monkeypatch: pytest.MonkeyPatch, channel: MagicMock, tmp_path: Path
):
    ca_file = tmp_path / "ca.pem"
    ca_file.write_bytes(b"-----BEGIN CERTIFICATE-----")
    ssl_channel_credentials = MagicMock()
    monkeypatch.setattr(
        grpc_module,
        "get_settings",
        lambda: _settings(
            NOTIFICATION_API_TLS=True, NOTIFICATION_API_CA_FILE=str(ca_file)
        ),
    )
    monkeypatch.setattr(
        grpc_module.grpc.aio, "secure_channel", MagicMock(return_value=channel)
    )
    monkeypatch.setattr(
        grpc_module.grpc, "ssl_channel_credentials", ssl_channel_credentials
    )

    client = grpc_module.GRPCClient()
    await client.connect("notifications:6781")

    ssl_channel_credentials.assert_called_once_with(
        root_certificates=b"-----BEGIN CERTIFICATE-----"
    )
