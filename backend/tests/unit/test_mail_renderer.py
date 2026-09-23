import pytest

from app.core.exceptions import MailTemplateInvalid
from app.mail_templates.context import AccountConfirmedContext
from app.mail_templates.plain_text import html_to_plain_text
from app.mail_templates.renderer import render_mail, unknown_variables
from app.mail_templates.texts import MailTemplateTexts

CONTEXT = AccountConfirmedContext(name="Ada", login_url="https://visit.test/link/abc")


def texts(**overrides: str) -> MailTemplateTexts:
    base = {
        "subject_de": "Konto frei",
        "subject_en": "Account ready",
        "body_de": "<p>Hallo {{ name }}</p>",
        "body_en": "<p>Hello {{ name }}</p>",
    }
    return MailTemplateTexts(**{**base, **overrides})


def test_rendered_subject_contains_both_languages():
    rendered = render_mail(texts(), CONTEXT, "test")

    assert rendered.subject == "Konto frei / Account ready"


def test_german_part_comes_before_the_english_part():
    rendered = render_mail(texts(), CONTEXT, "test")

    assert rendered.html.index("Hallo Ada") < rendered.html.index("Hello Ada")
    assert rendered.text.index("Hallo Ada") < rendered.text.index("Hello Ada")


def test_document_wraps_both_parts_with_a_divider_and_the_wordmark():
    rendered = render_mail(texts(), CONTEXT, "test")

    assert rendered.html.startswith("<!DOCTYPE html>")
    assert "<hr" in rendered.html
    assert ">VIS<" in rendered.html
    assert 'lang="de"' in rendered.html and 'lang="en"' in rendered.html


def test_values_are_html_escaped():
    rendered = render_mail(
        texts(),
        AccountConfirmedContext(name="<script>x</script>", login_url="https://a.test"),
        "test",
    )

    assert "<script>" not in rendered.html
    assert "&lt;script&gt;" in rendered.html


def test_unknown_variable_raises_the_typed_error_naming_it():
    with pytest.raises(MailTemplateInvalid) as error:
        render_mail(texts(body_de="<p>{{ nickname }}</p>"), CONTEXT, "test")

    assert error.value.code == "error.mail_template_invalid"
    assert error.value.status_code == 400
    assert "nickname" in error.value.message


def test_broken_syntax_raises_the_typed_error():
    with pytest.raises(MailTemplateInvalid):
        render_mail(texts(body_en="<p>{{ name </p>"), CONTEXT, "test")


def test_broken_syntax_names_the_failing_field_in_the_details():
    with pytest.raises(MailTemplateInvalid) as error:
        render_mail(texts(subject_en="{% for %}"), CONTEXT, "test")

    assert error.value.details == {"field": "subject_en"}


def test_unknown_variables_reports_names_outside_the_allowed_set():
    found = unknown_variables(
        "<p>{{ name }} {{ nickname }}</p>", frozenset({"name"}), "test", "body_de"
    )

    assert found == {"nickname"}


def test_unknown_variables_rejects_broken_syntax():
    with pytest.raises(MailTemplateInvalid) as error:
        unknown_variables("<p>{% for %}</p>", frozenset(), "test", "body_de")

    assert error.value.details == {"field": "body_de"}


def test_plain_text_keeps_links_with_their_url():
    text = html_to_plain_text('<p>Los: <a href="https://visit.test/x">hier</a></p>')

    assert text == "Los: hier (https://visit.test/x)"


def test_plain_text_drops_tags_and_collapses_whitespace():
    text = html_to_plain_text(
        "<html><head><style>p{color:red}</style></head>"
        "<body><h1>Titel</h1>\n  <p>Erste   Zeile<br />Zweite Zeile</p></body></html>"
    )

    assert text == "Titel\n\nErste Zeile\nZweite Zeile"


def test_plain_text_resolves_entities():
    assert html_to_plain_text("<p>Gr&uuml;sse &amp; Dank</p>") == "Grüsse & Dank"


def test_rendered_text_alternative_contains_the_link_url():
    rendered = render_mail(
        texts(body_de='<p><a href="{{ login_url }}">Zu VISIT</a></p>'), CONTEXT, "test"
    )

    assert "Zu VISIT (https://visit.test/link/abc)" in rendered.text
    assert "<p>" not in rendered.text
