import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import grpc
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.core import grpc as grpc_module
from app.core.config import get_settings
from app.generated.sip.notifications import mail_pb2, mail_pb2_grpc


@pytest.fixture
async def tls_server(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
    ca_path = tmp_path / "ca.pem"
    ca_path.write_bytes(certificate_pem)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    received_metadata = []

    class MailServer(mail_pb2_grpc.MailServiceServicer):
        async def SendMail(self, request, context):
            received_metadata.append(dict(context.invocation_metadata()))
            return mail_pb2.MailResponse()

        async def QueueMail(self, request, context):
            received_metadata.append(dict(context.invocation_metadata()))
            return mail_pb2.QueueResponse()

    server = grpc.aio.server()
    mail_pb2_grpc.add_MailServiceServicer_to_server(MailServer(), server)
    port = server.add_secure_port(
        "127.0.0.1:0", grpc.ssl_server_credentials([(key_pem, certificate_pem)])
    )
    await server.start()
    try:
        yield port, ca_path, received_metadata
    finally:
        await server.stop(0)


@pytest.mark.parametrize(
    "trust_ca, hostname",
    [(True, "localhost"), (False, "localhost"), (True, "127.0.0.1")],
)
async def test_actual_tls_and_bearer_authentication(
    tls_server, monkeypatch, trust_ca, hostname
):
    port, ca_path, received_metadata = tls_server
    settings = get_settings().model_copy(
        update={"NOTIFICATION_API_CA_FILE": str(ca_path) if trust_ca else None}
    )
    monkeypatch.setattr(grpc_module, "get_settings", lambda: settings)
    source = AsyncMock()
    source.get_access_token.return_value = "local-test-token"
    channel = grpc_module._create_channel(f"{hostname}:{port}", source)
    try:
        if not trust_ca or hostname != "localhost":
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(channel.channel_ready(), timeout=0.5)
            assert received_metadata == []
        else:
            await asyncio.wait_for(channel.channel_ready(), timeout=3)
            stub = mail_pb2_grpc.MailServiceStub(channel)
            await stub.SendMail(mail_pb2.Mail(subject="test"), timeout=3)
            await stub.QueueMail(mail_pb2.Mail(subject="test"), timeout=3)
            assert len(received_metadata) == 2
            assert all(
                metadata["authorization"] == "Bearer local-test-token"
                for metadata in received_metadata
            )
    finally:
        await channel.close()
