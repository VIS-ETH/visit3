from unittest.mock import AsyncMock

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


async def test_send_mail_delegates_to_grpc_stub():
    stub = AsyncMock()
    service = MailService(stub)
    message = service.construct_mail(["to@example.com"], "Subject", plain_text="Hello")

    await service.send_mail(message)

    stub.SendMail.assert_awaited_once_with(message)
