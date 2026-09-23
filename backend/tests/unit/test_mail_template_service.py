from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from app.mail_templates.context import (
    AccountAwaitingConfirmationContext,
    PasswordResetContext,
)
from app.mail_templates.defaults import MAIL_TEMPLATE_DEFAULTS
from app.mail_templates.keys import MailTemplateKey
from app.models.kp_event import KpEvent
from app.models.mail import MailTemplate
from app.repositories.mail_repository import MailTemplateRepository
from app.services.mail_service import MailService
from app.services.mail_template_service import MailTemplateService
from app.services.notification_recipients import NotificationRecipients

CONTEXT = PasswordResetContext(name="Ada", reset_url="https://visit.test/reset/abc")
STAFF_KEY = MailTemplateKey.ACCOUNT_AWAITING_CONFIRMATION
STAFF_CONTEXT = AccountAwaitingConfirmationContext(
    name="Ada", email="ada@example.com", admin_url="https://visit.test/admin"
)


@pytest.fixture
def mail_template_repo() -> AsyncMock:
    return AsyncMock(spec=MailTemplateRepository)


@pytest.fixture
def notification_recipients() -> AsyncMock:
    return AsyncMock(spec=NotificationRecipients)


@pytest.fixture
def mail_stub() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def template_service(
    mail_template_repo: AsyncMock,
    notification_recipients: AsyncMock,
    mail_stub: AsyncMock,
) -> MailTemplateService:
    return MailTemplateService(
        mail_template_repo, notification_recipients, MailService(mail_stub)
    )


def kp_event(
    name: str, days_from_today: int, notification_email: str | None = None
) -> KpEvent:
    today = date.today()
    return KpEvent(
        name=name,
        registration_open=today + timedelta(days=days_from_today - 5),
        registration_end=today + timedelta(days=days_from_today + 5),
        finalization_deadline=today + timedelta(days=days_from_today + 6),
        nametags_deadline=today + timedelta(days=days_from_today + 7),
        event_date=today + timedelta(days=days_from_today + 30),
        notification_email=notification_email,
    )


async def test_missing_row_falls_back_to_the_code_default(
    template_service: MailTemplateService, mail_template_repo: AsyncMock
):
    mail_template_repo.get_by_key.return_value = None

    texts = await template_service.texts_for(MailTemplateKey.PASSWORD_RESET)

    assert texts == MAIL_TEMPLATE_DEFAULTS[MailTemplateKey.PASSWORD_RESET]


async def test_stored_row_overrides_the_default(
    template_service: MailTemplateService, mail_template_repo: AsyncMock
):
    mail_template_repo.get_by_key.return_value = MailTemplate(
        key=str(MailTemplateKey.PASSWORD_RESET),
        subject_de="Eigener Betreff",
        subject_en="Custom subject",
        body_de="<p>DE {{ name }}</p>",
        body_en="<p>EN {{ name }}</p>",
    )

    rendered = await template_service.render(MailTemplateKey.PASSWORD_RESET, CONTEXT)

    assert rendered.subject == "Eigener Betreff / Custom subject"
    assert "DE Ada" in rendered.html


async def test_send_builds_a_multipart_message(
    template_service: MailTemplateService,
    mail_template_repo: AsyncMock,
    mail_stub: AsyncMock,
):
    mail_template_repo.get_by_key.return_value = None

    await template_service.send(
        MailTemplateKey.PASSWORD_RESET, ["user@example.com"], CONTEXT
    )

    mail_stub.SendMail.assert_awaited_once()
    message = mail_stub.SendMail.await_args.args[0]
    assert message.to[0].mail_address.address == "user@example.com"
    content_types = [part.content_type for part in message.multipart_body.parts]
    assert content_types == ["text/plain; charset=utf-8", "text/html; charset=utf-8"]
    assert message.multipart_body.parts[1].content.startswith("<!DOCTYPE html>")


async def test_send_without_recipients_does_nothing(
    template_service: MailTemplateService, mail_stub: AsyncMock
):
    await template_service.send(MailTemplateKey.PASSWORD_RESET, [], CONTEXT)

    mail_stub.SendMail.assert_not_awaited()


async def test_staff_notification_uses_the_resolved_recipient(
    template_service: MailTemplateService,
    mail_template_repo: AsyncMock,
    notification_recipients: AsyncMock,
    mail_stub: AsyncMock,
):
    mail_template_repo.get_by_key.return_value = None
    notification_recipients.staff_notification_email.return_value = "kp@example.com"

    await template_service.send_to_staff_notification(STAFF_KEY, STAFF_CONTEXT)

    message = mail_stub.SendMail.await_args.args[0]
    assert message.to[0].mail_address.address == "kp@example.com"


async def test_notification_email_prefers_the_open_event(kp_repo: AsyncMock):
    kp_repo.list_kps.return_value = [
        kp_event("Past", -60, "past@example.com"),
        kp_event("Open", 0, "open@example.com"),
    ]

    recipients = NotificationRecipients(kp_repo)

    assert await recipients.staff_notification_email() == "open@example.com"


async def test_notification_email_falls_back_when_the_field_is_unset(
    kp_repo: AsyncMock,
):
    kp_repo.list_kps.return_value = [kp_event("Open", 0)]

    recipients = NotificationRecipients(kp_repo)

    assert await recipients.staff_notification_email() == "kontaktparty@vis.ethz.ch"


async def test_notification_email_falls_back_without_events(kp_repo: AsyncMock):
    kp_repo.list_kps.return_value = []

    recipients = NotificationRecipients(kp_repo)

    assert await recipients.staff_notification_email() == "kontaktparty@vis.ethz.ch"
