import pytest

from app.mail_templates.context import SAMPLE_CONTEXTS, allowed_variables
from app.mail_templates.defaults import MAIL_TEMPLATE_DEFAULTS
from app.mail_templates.keys import MailTemplateKey
from app.mail_templates.renderer import render_mail, unknown_variables


def test_every_key_has_a_default_and_a_sample_context():
    assert set(MAIL_TEMPLATE_DEFAULTS) == set(MailTemplateKey)
    assert set(SAMPLE_CONTEXTS) == set(MailTemplateKey)


@pytest.mark.parametrize("key", sorted(MailTemplateKey))
def test_defaults_only_use_declared_variables(key: MailTemplateKey):
    texts = MAIL_TEMPLATE_DEFAULTS[key]
    allowed = allowed_variables(key)

    for field in ("subject_de", "subject_en", "body_de", "body_en"):
        source = getattr(texts, field)
        assert unknown_variables(source, allowed, str(key), field) == set()


@pytest.mark.parametrize("key", sorted(MailTemplateKey))
def test_defaults_render_with_the_sample_context(key: MailTemplateKey):
    rendered = render_mail(MAIL_TEMPLATE_DEFAULTS[key], SAMPLE_CONTEXTS[key], str(key))

    assert rendered.subject
    assert rendered.text
    assert "{{" not in rendered.html


def test_the_confirmation_mail_explains_what_can_still_change():
    texts = MAIL_TEMPLATE_DEFAULTS[MailTemplateKey.BOOKING_ACCEPTED]

    assert "but no longer change the booth zone" in texts.body_en
    assert "die Standzone aber nicht mehr ändern" in texts.body_de
