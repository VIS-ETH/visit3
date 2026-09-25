from unittest.mock import AsyncMock

from app.core.config import get_settings
from app.services import mail_service as mail_module
from app.services.mail_service import MailService


def test_construct_mail_builds_plain_text_message():
    service = MailService(AsyncMock())

    message = service.construct_mail(
        ["to@example.com"],
        "Subject",
        plain_text="Hello",
        email_from="from@example.com",
    )

    assert message is not None
    assert message.subject == "Subject"
    assert message.plain_text == "Hello"
    assert message.to[0].mail_address.address == "to@example.com"
    assert getattr(message, "from").mail_address.address == "from@example.com"


def test_construct_mail_returns_none_without_body_or_recipient():
    service = MailService(AsyncMock())

    assert service.construct_mail(["to@example.com"], "Subject") is None
    assert service.construct_mail([], "Subject", plain_text="Hello") is None


def test_construct_mail_uses_the_authorized_default_sender():
    message = MailService(AsyncMock()).construct_mail(
        ["to@example.com"], "Subject", plain_text="Hello"
    )
    assert message is not None
    assert message.HasField("from")
    assert getattr(message, "from").mail_address.address == "visit@vis.ethz.ch"


def test_construct_mail_uses_the_configured_sender(monkeypatch):
    settings = get_settings().model_copy(
        update={"NOTIFICATION_SENDER_EMAIL": "custom@example.com"}
    )
    monkeypatch.setattr(mail_module, "get_settings", lambda: settings)
    message = MailService(AsyncMock()).construct_mail(
        ["to@example.com"], "Subject", plain_text="Hello"
    )
    assert getattr(message, "from").mail_address.address == "custom@example.com"


async def test_send_mail_delegates_to_grpc_stub():
    stub = AsyncMock()
    service = MailService(stub)
    message = service.construct_mail(["to@example.com"], "Subject", plain_text="Hello")

    await service.send_mail(message)

    stub.SendMail.assert_awaited_once_with(message)
