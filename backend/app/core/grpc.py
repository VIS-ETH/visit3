import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import grpc
import grpc.aio

from app.core.config import get_oauth_settings, get_settings
from app.core.service_account import ServiceAccountCredential
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub

logger = logging.getLogger(__name__)


class OAuthInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    """Authenticate every RPC exposed by the notifications API (Send/QueueMail)."""

    def __init__(self, credentials: ServiceAccountCredential):
        self.credentials = credentials

    async def intercept_unary_unary(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], Awaitable[Any]],
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        token = await self.credentials.get_access_token()
        metadata = grpc.aio.Metadata()
        for key, value in client_call_details.metadata or ():
            if key.lower() != "authorization":
                metadata.add(key, value)
        metadata.add("authorization", f"Bearer {token}")
        details = grpc.aio.ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials,
            client_call_details.wait_for_ready,
        )
        return await continuation(details, request)


def _create_channel(
    target: str, credentials: ServiceAccountCredential
) -> grpc.aio.Channel:
    settings = get_settings()
    interceptors = [OAuthInterceptor(credentials)]
    if not settings.NOTIFICATION_API_TLS:
        return grpc.aio.insecure_channel(target, interceptors=interceptors)
    root_certificates = (
        Path(settings.NOTIFICATION_API_CA_FILE).read_bytes()
        if settings.NOTIFICATION_API_CA_FILE
        else None
    )
    tls_credentials = grpc.ssl_channel_credentials(root_certificates=root_certificates)
    return grpc.aio.secure_channel(target, tls_credentials, interceptors=interceptors)


class GRPCClient:
    def __init__(self):
        self.channel: grpc.aio.Channel | None = None
        self.stub: MailServiceStub | None = None
        self.credentials: ServiceAccountCredential | None = None

    async def connect(self, target: str):
        self.credentials = ServiceAccountCredential(get_oauth_settings())
        try:
            # Fail startup before accepting requests if credentials are invalid.
            await self.credentials.start()
            self.channel = _create_channel(target, self.credentials)
            await asyncio.wait_for(self.channel.channel_ready(), timeout=10)
            self.stub = MailServiceStub(self.channel)
            logger.info("Notification API gRPC channel ready")
        except BaseException as error:
            await self.disconnect()
            if isinstance(error, TimeoutError):
                raise RuntimeError(
                    "notification API gRPC connection timed out"
                ) from None
            raise

    async def disconnect(self):
        try:
            if self.channel is not None:
                await self.channel.close()
        finally:
            self.channel = None
            self.stub = None
            if self.credentials is not None:
                await self.credentials.close()
                self.credentials = None


grpc_client = GRPCClient()


def mail_stub() -> MailServiceStub:
    if grpc_client.stub is None:
        raise RuntimeError("grpc_client:not_connected")
    return grpc_client.stub
