from email.header import decode_header, make_header
from unittest.mock import AsyncMock

from google.protobuf.json_format import MessageToDict

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
    assert MessageToDict(message)["from"] == {
        "mailAddress": {
            "name": "VISIT MAIL SERVICE",
            "address": "visit@vis.ethz.ch",
        }
    }


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


PROBE = "ä ö ü Ä Ö Ü ß é € 🎉"


def decoded(header: str) -> str:
    return str(make_header(decode_header(header)))


def test_construct_mail_encodes_a_non_ascii_subject():
    message = MailService(AsyncMock()).construct_mail(
        ["to@example.com"],
        f"VISIT: Buchung für Kontaktparty bestätigt {PROBE}",
        plain_text="Hello",
    )

    assert message is not None
    assert message.subject.isascii()
    assert message.subject.startswith("=?utf-8?")
    assert decoded(message.subject) == (
        f"VISIT: Buchung für Kontaktparty bestätigt {PROBE}"
    )


def test_construct_mail_keeps_an_ascii_subject_readable():
    message = MailService(AsyncMock()).construct_mail(
        ["to@example.com"], "VISIT: Account activated", plain_text="Hello"
    )

    assert message is not None
    assert message.subject == "VISIT: Account activated"


def test_construct_mail_leaves_the_sender_name_to_the_notifications_api():
    message = MailService(AsyncMock()).construct_mail(
        ["to@example.com"],
        "Subject",
        plain_text=f"Grüße {PROBE}",
        sender_name=f"VISIT Ärger {PROBE}",
    )

    assert message is not None
    assert getattr(message, "from").mail_address.name == f"VISIT Ärger {PROBE}"
    assert message.plain_text == f"Grüße {PROBE}"
