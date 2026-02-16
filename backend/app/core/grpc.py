import grpc
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub


class GRPCClient:
    def __init__(self):
        self.channel = None
        self.stub = None

    async def connect(self, target: str):
        self.channel = grpc.aio.insecure_channel(target)
        self.stub = MailServiceStub(self.channel)

    async def disconnect(self):
        if self.channel:
            await self.channel.close()


grpc_client = GRPCClient()
