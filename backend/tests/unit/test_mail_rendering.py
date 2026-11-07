import logging
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import MailTemplateInvalid
from app.mail_templates.campaign import render_campaign_mail, validate_campaign_texts
from app.mail_templates.context import (
    MAIL_CAMPAIGN_SAMPLE_CONTEXT,
    CompanyInviteContext,
    PasswordResetContext,
)
from app.mail_templates.defaults import MAIL_TEMPLATE_DEFAULTS
from app.mail_templates.keys import MailTemplateKey
from app.mail_templates.plain_text import html_to_plain_text
from app.mail_templates.renderer import MAX_SUBJECT_CHARACTERS, render_mail
from app.mail_templates.texts import MailTemplateTexts
from app.models.mail import MailTemplate
from app.repositories.mail_repository import MailTemplateRepository
from app.services.mail_service import MailService
from app.services.mail_template_service import MailTemplateService, validate_texts
from app.services.notification_recipients import NotificationRecipients

IDENTIFIER = "mail_campaign:test"
COMPARES_NAME_WITH_A_NUMBER = (
    '<p>{% if company_name == "Acme AG" or company_name < 1 %}hi{% endif %}</p>'
)


def campaign_texts(**overrides: str) -> MailTemplateTexts:
    return replace(
        MailTemplateTexts(
            subject_de="Hallo {{ company_name }}",
            subject_en="",
            body_de="<p>Hallo</p>",
            body_en="",
        ),
        **overrides,
    )


def test_system_mail_subjects_are_not_html_escaped():
    rendered = render_mail(
        MAIL_TEMPLATE_DEFAULTS[MailTemplateKey.COMPANY_INVITE],
        CompanyInviteContext(company_name="Ernst & Young", invite_url="https://x/i"),
        "company_invite",
    )

    assert "Ernst & Young" in rendered.subject
    assert "&amp;" not in rendered.subject


def test_campaign_subjects_are_not_html_escaped():
    context = replace(MAIL_CAMPAIGN_SAMPLE_CONTEXT, company_name="O'Reilly & Söhne")

    rendered = render_campaign_mail(campaign_texts(), context, IDENTIFIER)

    assert rendered.subject == "Hallo O'Reilly & Söhne"


def test_campaign_bodies_stay_html_escaped():
    context = replace(MAIL_CAMPAIGN_SAMPLE_CONTEXT, company_name="O'Reilly & Söhne")
    texts = campaign_texts(body_de="<p>{{ company_name }}</p>")

    rendered = render_campaign_mail(texts, context, IDENTIFIER)

    assert "O&#39;Reilly &amp; Söhne" in rendered.html


def test_long_subjects_are_cut_to_the_header_limit():
    context = replace(MAIL_CAMPAIGN_SAMPLE_CONTEXT, company_name="A" * 1000)

    rendered = render_campaign_mail(campaign_texts(), context, IDENTIFIER)

    assert len(rendered.subject) == MAX_SUBJECT_CHARACTERS


def test_a_data_dependent_template_error_is_a_template_error():
    texts = campaign_texts(body_de=COMPARES_NAME_WITH_A_NUMBER)
    validate_campaign_texts(texts, IDENTIFIER)
    context = replace(MAIL_CAMPAIGN_SAMPLE_CONTEXT, company_name="Other AG")

    with pytest.raises(MailTemplateInvalid):
        render_campaign_mail(texts, context, IDENTIFIER)


def test_a_type_error_in_a_system_template_fails_validation():
    texts = MailTemplateTexts(
        subject_de="s",
        subject_en="s",
        body_de="{{ reset_url }} {{ 1 < 'a' }}",
        body_en="{{ reset_url }}",
    )

    with pytest.raises(MailTemplateInvalid):
        validate_texts(MailTemplateKey.PASSWORD_RESET, texts)


@pytest.mark.parametrize(
    ("key", "variable"),
    [
        (MailTemplateKey.ACCOUNT_CONFIRM_EMAIL, "confirm_url"),
        (MailTemplateKey.EMAIL_CHANGE_CONFIRM, "confirm_url"),
        (MailTemplateKey.PASSWORD_RESET, "reset_url"),
        (MailTemplateKey.COMPANY_INVITE, "invite_url"),
    ],
)
def test_system_templates_must_contain_their_link(key: MailTemplateKey, variable: str):
    with_link = MailTemplateTexts(
        subject_de="s",
        subject_en="s",
        body_de=f"<p>{{{{ {variable} }}}}</p>",
        body_en=f"<p>{{{{ {variable} }}}}</p>",
    )
    validate_texts(key, with_link)

    with pytest.raises(MailTemplateInvalid) as raised:
        validate_texts(key, replace(with_link, body_en="<p>Hello</p>"))

    assert raised.value.details == {"field": "body_en", "variable": variable}


async def test_a_stored_template_failing_at_send_time_falls_back_to_the_default(
    caplog: pytest.LogCaptureFixture,
):
    repository = AsyncMock(spec=MailTemplateRepository)
    repository.get_by_key.return_value = MailTemplate(
        key=str(MailTemplateKey.PASSWORD_RESET),
        subject_de="s",
        subject_en="s",
        body_de='{{ reset_url }}{% if name == "Max Muster" or name < 1 %}x{% endif %}',
        body_en="{{ reset_url }}",
    )
    mail_stub = AsyncMock()
    service = MailTemplateService(
        repository, AsyncMock(spec=NotificationRecipients), MailService(mail_stub)
    )

    with caplog.at_level(logging.ERROR):
        await service.send(
            MailTemplateKey.PASSWORD_RESET,
            ["user@example.com"],
            PasswordResetContext(name="Real User", reset_url="https://x/r"),
        )

    message = mail_stub.SendMail.await_args.args[0]
    default = MAIL_TEMPLATE_DEFAULTS[MailTemplateKey.PASSWORD_RESET]
    assert default.subject_en in message.subject
    assert "https://x/r" in message.plain_text
    assert [r for r in caplog.records if r.levelno == logging.ERROR]


def test_plain_text_separates_table_cells():
    html = "<table><tr><td>Datum</td><td>20.10.</td></tr></table>"

    assert html_to_plain_text(html) == "Datum | 20.10."


def test_plain_text_marks_list_items():
    assert html_to_plain_text("<ol><li>eins</li><li>zwei</li></ol>") == (
        "1. eins\n2. zwei"
    )
    assert html_to_plain_text("<ul><li>eins</li><li>zwei</li></ul>") == (
        "- eins\n- zwei"
    )


def test_plain_text_keeps_the_url_of_an_unclosed_link():
    assert html_to_plain_text('<p><a href="https://x/l">Login</p>') == (
        "Login (https://x/l)"
    )


def test_plain_text_does_not_repeat_a_url_shown_as_the_link_text():
    assert html_to_plain_text('<a href="https://x/l">https://x/l</a>') == (
        "https://x/l"
    )
