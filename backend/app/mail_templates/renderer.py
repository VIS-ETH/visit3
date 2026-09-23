from collections.abc import Mapping
from dataclasses import dataclass

from jinja2 import StrictUndefined, TemplateError
from jinja2.meta import find_undeclared_variables
from jinja2.sandbox import SandboxedEnvironment

from app.core.exceptions import MailTemplateInvalid
from app.mail_templates.context import MailContext
from app.mail_templates.plain_text import html_to_plain_text
from app.mail_templates.texts import MailTemplateTexts

WORDMARK = "VIS"
BODY_STYLE = "margin:0;padding:0;background-color:#f4f5f7;"
CONTAINER_STYLE = (
    "max-width:600px;margin:0 auto;padding:24px 16px;background-color:#ffffff;"
    "font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:1.5;"
    "color:#1a1b1e;"
)
WORDMARK_STYLE = (
    "margin:0 0 24px 0;font-size:20px;font-weight:700;letter-spacing:0.08em;"
)
DIVIDER_STYLE = "border:0;border-top:1px solid #d0d1d4;margin:24px 0;"

environment = SandboxedEnvironment(autoescape=True, undefined=StrictUndefined)


@dataclass(frozen=True)
class RenderedMail:
    subject: str
    html: str
    text: str


def unknown_variables(
    source: str, allowed: frozenset[str], identifier: str, field: str
) -> set[str]:
    try:
        parsed = environment.parse(source)
    except TemplateError as error:
        raise MailTemplateInvalid(identifier, str(error), field)
    return find_undeclared_variables(parsed) - allowed


def render_fragment(
    source: str, variables: Mapping[str, str], identifier: str, field: str
) -> str:
    try:
        return environment.from_string(source).render(**variables)
    except TemplateError as error:
        raise MailTemplateInvalid(identifier, str(error), field)


def compose_document(body_de: str, body_en: str) -> str:
    return (
        "<!DOCTYPE html>"
        '<html lang="de">'
        '<head><meta charset="utf-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />'
        "</head>"
        f'<body style="{BODY_STYLE}">'
        f'<div style="{CONTAINER_STYLE}">'
        f'<p style="{WORDMARK_STYLE}">{WORDMARK}</p>'
        f'<div lang="de">{body_de}</div>'
        f'<hr style="{DIVIDER_STYLE}" />'
        f'<div lang="en">{body_en}</div>'
        "</div></body></html>"
    )


def render_mail(
    texts: MailTemplateTexts, context: MailContext, identifier: str
) -> RenderedMail:
    variables = context.variables()
    subject_de = render_fragment(texts.subject_de, variables, identifier, "subject_de")
    subject_en = render_fragment(texts.subject_en, variables, identifier, "subject_en")
    body_de = render_fragment(texts.body_de, variables, identifier, "body_de")
    body_en = render_fragment(texts.body_en, variables, identifier, "body_en")
    html = compose_document(body_de, body_en)
    return RenderedMail(
        subject=f"{subject_de} / {subject_en}",
        html=html,
        text=html_to_plain_text(html),
    )
