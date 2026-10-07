import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from jinja2 import StrictUndefined, TemplateError, nodes
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

MAX_TEMPLATE_CHARACTERS = 50_000
MAX_OUTPUT_CHARACTERS = 100_000
ALLOWED_NODES = (
    nodes.Output,
    nodes.TemplateData,
    nodes.Name,
    nodes.Const,
    nodes.If,
    nodes.CondExpr,
    nodes.Not,
    nodes.And,
    nodes.Or,
    nodes.Compare,
    nodes.Operand,
    nodes.Filter,
)
ALLOWED_FILTERS = frozenset(
    {"capitalize", "default", "e", "escape", "lower", "title", "trim", "upper"}
)

environment = SandboxedEnvironment(autoescape=True, undefined=StrictUndefined)


def _unsupported(node: nodes.Node) -> str | None:
    if not isinstance(node, ALLOWED_NODES):
        return type(node).__name__
    if isinstance(node, nodes.Filter) and node.name not in ALLOWED_FILTERS:
        return f"filter {node.name}"
    return None


def parse_template(source: str, identifier: str, field: str) -> nodes.Template:
    try:
        parsed = environment.parse(source)
    except TemplateError as error:
        raise MailTemplateInvalid(identifier, str(error), field)
    for node in parsed.find_all(nodes.Node):
        unsupported = _unsupported(node)
        if unsupported is not None:
            raise MailTemplateInvalid(
                identifier, f"unsupported syntax: {unsupported}", field
            )
    return parsed


@dataclass(frozen=True)
class RenderedMail:
    subject: str
    html: str
    text: str


def unknown_variables(
    source: str, allowed: frozenset[str], identifier: str, field: str
) -> set[str]:
    return (
        find_undeclared_variables(parse_template(source, identifier, field)) - allowed
    )


def render_fragment(
    source: str, variables: Mapping[str, str], identifier: str, field: str
) -> str:
    parsed = parse_template(source, identifier, field)
    try:
        rendered = environment.from_string(parsed).render(**variables)
    except TemplateError as error:
        raise MailTemplateInvalid(identifier, str(error), field)
    if len(rendered) > MAX_OUTPUT_CHARACTERS:
        raise MailTemplateInvalid(identifier, "output too large", field)
    return rendered


def compose_sections(sections: Sequence[tuple[str, str]]) -> str:
    divider = f'<hr style="{DIVIDER_STYLE}" />'
    content = divider.join(
        f'<div lang="{language}">{body}</div>' for language, body in sections
    )
    return (
        "<!DOCTYPE html>"
        '<html lang="de">'
        '<head><meta charset="utf-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />'
        "</head>"
        f'<body style="{BODY_STYLE}">'
        f'<div style="{CONTAINER_STYLE}">'
        f'<p style="{WORDMARK_STYLE}">{WORDMARK}</p>'
        f"{content}"
        "</div></body></html>"
    )


def compose_document(body_de: str, body_en: str) -> str:
    return compose_sections([("de", body_de), ("en", body_en)])


def header_safe(text: str) -> str:
    return " ".join(
        "".join(
            " " if unicodedata.category(character) == "Cc" else character
            for character in text
        ).split()
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
