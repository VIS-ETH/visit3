import asyncio
import logging
from pathlib import Path

import grpc
import grpc.aio

from app.core.config import get_settings
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub

logger = logging.getLogger(__name__)


def _create_channel(target: str) -> grpc.aio.Channel:
    settings = get_settings()
    if not settings.NOTIFICATION_API_TLS:
        return grpc.aio.insecure_channel(target)
    root_certificates = (
        Path(settings.NOTIFICATION_API_CA_FILE).read_bytes()
        if settings.NOTIFICATION_API_CA_FILE
        else None
    )
    credentials = grpc.ssl_channel_credentials(root_certificates=root_certificates)
    return grpc.aio.secure_channel(target, credentials)


class GRPCClient:
    def __init__(self):
        self.channel = None
        self.stub = None

    async def connect(self, target: str):
        self.channel = _create_channel(target)
        self.stub = MailServiceStub(self.channel)
        try:
            await asyncio.wait_for(self.channel.channel_ready(), timeout=10)
            logger.info(f"gRPC channel ready: {target}")
        except TimeoutError as e:
            logger.error(f"gRPC channel not ready after timeout: {target}")
            raise RuntimeError(f"grpc_connect_timeout:{target}") from e

    async def disconnect(self):
        if self.channel:
            await self.channel.close()


grpc_client = GRPCClient()


def mail_stub() -> MailServiceStub:
    if grpc_client.stub is None:
        raise RuntimeError("grpc_client:not_connected")
    return grpc_client.stub
