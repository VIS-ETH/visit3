from dataclasses import replace

import pytest
from pydantic import ValidationError

from app.core.exceptions import MailTemplateInvalid
from app.mail_templates.campaign import render_campaign_mail, validate_campaign_texts
from app.mail_templates.context import MAIL_CAMPAIGN_SAMPLE_CONTEXT
from app.mail_templates.texts import MailTemplateTexts
from app.schemas.mail_campaign import MailCampaignTextsInput

IDENTIFIER = "mail_campaign:test"
TEXTS = MailTemplateTexts(
    subject_de="Erinnerung für {{ company_name }}",
    subject_en="Reminder for {{ company_name }}",
    body_de="<p>Hallo {{ name }}, Anmeldeschluss ist am {{ registration_end }}.</p>",
    body_en="<p>Hello {{ name }}, registration closes on {{ registration_end }}.</p>",
)
GERMAN_ONLY = replace(TEXTS, subject_en="", body_en="")


def test_both_languages_are_rendered_with_the_variables():
    rendered = render_campaign_mail(TEXTS, MAIL_CAMPAIGN_SAMPLE_CONTEXT, IDENTIFIER)

    assert rendered.subject == "Erinnerung für Acme AG / Reminder for Acme AG"
    assert "Hallo Ada Lovelace, Anmeldeschluss ist am 2026-09-15." in rendered.text
    assert "Hello Ada Lovelace, registration closes on 2026-09-15." in rendered.text
    assert rendered.text.index("Hallo") < rendered.text.index("Hello")


def test_without_english_texts_only_german_is_sent():
    rendered = render_campaign_mail(
        GERMAN_ONLY, MAIL_CAMPAIGN_SAMPLE_CONTEXT, IDENTIFIER
    )

    assert rendered.subject == "Erinnerung für Acme AG"
    assert 'lang="en"' not in rendered.html
    assert "Hello" not in rendered.text


def test_variables_are_html_escaped():
    context = replace(MAIL_CAMPAIGN_SAMPLE_CONTEXT, name='<img src=x onerror="1">')

    rendered = render_campaign_mail(TEXTS, context, IDENTIFIER)

    assert "<img" not in rendered.html
    assert "&lt;img" in rendered.html


def test_variables_cannot_inject_mail_headers_into_the_subject():
    context = replace(
        MAIL_CAMPAIGN_SAMPLE_CONTEXT, company_name="Acme\r\nBcc: victim@example.com"
    )

    rendered = render_campaign_mail(TEXTS, context, IDENTIFIER)

    assert "\r" not in rendered.subject
    assert "\n" not in rendered.subject
    assert rendered.subject.startswith("Erinnerung für Acme Bcc: victim@example.com")


def test_known_variables_validate():
    validate_campaign_texts(TEXTS, IDENTIFIER)
    validate_campaign_texts(GERMAN_ONLY, IDENTIFIER)


def test_unknown_variables_are_rejected_with_their_field():
    texts = replace(TEXTS, body_en="<p>{{ password }}</p>")

    with pytest.raises(MailTemplateInvalid) as error:
        validate_campaign_texts(texts, IDENTIFIER)

    assert error.value.details == {"field": "body_en", "variable": "password"}


@pytest.mark.parametrize(
    "source",
    [
        "{{ name.__class__.__mro__ }}",
        "{% for item in name %}{{ item }}{% endfor %}",
        "{{ name | attr('upper') }}",
        "{{ lipsum.__globals__ }}",
        "{% include 'secret' %}",
    ],
)
def test_unsafe_template_syntax_is_rejected(source: str):
    with pytest.raises(MailTemplateInvalid) as error:
        validate_campaign_texts(replace(TEXTS, body_de=source), IDENTIFIER)

    assert error.value.details is not None
    assert error.value.details["field"] == "body_de"


@pytest.mark.parametrize("subject", ["Hallo\r\nBcc: x@example.com", "Tab\tin\x00"])
def test_subjects_with_control_characters_are_rejected(subject: str):
    with pytest.raises(ValidationError):
        MailCampaignTextsInput(subject_de=subject, body_de="<p>Hallo</p>")


def test_the_english_subject_and_body_belong_together():
    with pytest.raises(ValidationError):
        MailCampaignTextsInput(
            subject_de="Hallo", body_de="<p>Hallo</p>", subject_en="Hello"
        )
