from unittest.mock import AsyncMock

import pytest

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


async def test_send_confirm_email_mail_sends_expected_link():
    service = MailService(AsyncMock())
    service.send_mail = AsyncMock()

    await service.send_confirm_email_mail("to@example.com", "token-123")

    service.send_mail.assert_awaited_once()
    message = service.send_mail.await_args.args[0]
    assert message.subject == "Confirm Your Account For VISIT"
    assert message.to[0].mail_address.address == "to@example.com"
    assert "http://localhost:3000/confirm-email/token-123" in message.plain_text


async def test_send_reset_password_mail_sends_expected_link():
    service = MailService(AsyncMock())
    service.send_mail = AsyncMock()

    await service.send_reset_password_mail("to@example.com", "token-123")

    service.send_mail.assert_awaited_once()
    message = service.send_mail.await_args.args[0]
    assert message.subject == "VISIT Reset Password"
    assert "http://localhost:3000/reset/token-123" in message.plain_text


async def test_send_company_invite_mail_sends_expected_link():
    service = MailService(AsyncMock())
    service.send_mail = AsyncMock()

    await service.send_company_invite_mail(
        "to@example.com", "Acme AG", "token-123"
    )

    service.send_mail.assert_awaited_once()
    message = service.send_mail.await_args.args[0]
    assert message.subject == "You've been invited to join Acme AG on VISIT"
    assert "http://localhost:3000/company/join/token-123" in message.plain_text


def test_construct_mail_builds_multipart_body():
    service = MailService(AsyncMock())

    multipart = MailService.Mimebody(
        [
            MailService.Mimebody.Multipart("text/plain", "Hello"),
            MailService.Mimebody.Multipart("text/html", "<p>Hello</p>"),
        ]
    )
    message = service.construct_mail(
        ["to@example.com"],
        "Subject",
        multipart_body=multipart,
    )

    assert message is not None
    assert message.subject == "Subject"
    assert len(message.multipart_body.parts) == 2
    assert message.multipart_body.parts[0].content_type == "text/plain"
    assert message.multipart_body.parts[0].content == "Hello"


async def test_send_mail_raises_on_grpc_error():
    stub = AsyncMock()
    stub.SendMail.side_effect = Exception("gRPC failed")
    service = MailService(stub)
    message = service.construct_mail(["to@example.com"], "Subject", plain_text="Hello")

    with pytest.raises(Exception, match="gRPC failed"):
        await service.send_mail(message)


async def test_send_confirm_email_mail_skips_send_when_construct_returns_none():
    service = MailService(AsyncMock())
    service.construct_mail = lambda *args, **kwargs: None
    service.send_mail = AsyncMock()

    await service.send_confirm_email_mail("to@example.com", "token-123")

    service.send_mail.assert_not_awaited()
