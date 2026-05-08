import asyncio
import logging

import grpc
import grpc.aio

from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub

logger = logging.getLogger(__name__)


class GRPCClient:
    def __init__(self):
        self.channel = None
        self.stub = None

    async def connect(self, target: str):
        self.channel = grpc.aio.insecure_channel(target)
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
