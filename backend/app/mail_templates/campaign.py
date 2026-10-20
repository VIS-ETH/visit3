from uuid import UUID

from app.core.exceptions import MailTemplateInvalid
from app.mail_templates.context import MAIL_CAMPAIGN_SAMPLE_CONTEXT, MailCampaignContext
from app.mail_templates.plain_text import html_to_plain_text
from app.mail_templates.renderer import (
    RenderedMail,
    compose_sections,
    header_safe,
    render_fragment,
    unknown_variables,
)
from app.mail_templates.texts import MailTemplateTexts

CAMPAIGN_VARIABLES = MailCampaignContext.variable_names()
SUBJECT_SEPARATOR = " / "


def campaign_identifier(campaign_id: UUID | None) -> str:
    return f"mail_campaign:{campaign_id or 'draft'}"


def has_english(texts: MailTemplateTexts) -> bool:
    return bool(texts.subject_en.strip() or texts.body_en.strip())


def campaign_fields(texts: MailTemplateTexts) -> list[tuple[str, str]]:
    fields = [("subject_de", texts.subject_de), ("body_de", texts.body_de)]
    if has_english(texts):
        fields += [("subject_en", texts.subject_en), ("body_en", texts.body_en)]
    return fields


def validate_campaign_texts(texts: MailTemplateTexts, identifier: str) -> None:
    sample = MAIL_CAMPAIGN_SAMPLE_CONTEXT.variables()
    for field, source in campaign_fields(texts):
        unknown = sorted(
            unknown_variables(source, CAMPAIGN_VARIABLES, identifier, field)
        )
        if unknown:
            raise MailTemplateInvalid(
                identifier,
                f"unknown variable '{unknown[0]}' in {field}",
                field,
                unknown[0],
            )
        render_fragment(source, sample, identifier, field)


def render_campaign_mail(
    texts: MailTemplateTexts, context: MailCampaignContext, identifier: str
) -> RenderedMail:
    variables = context.variables()
    rendered = {
        field: render_fragment(source, variables, identifier, field)
        for field, source in campaign_fields(texts)
    }
    subjects = [header_safe(rendered["subject_de"])]
    sections = [("de", rendered["body_de"])]
    if "subject_en" in rendered:
        subjects.append(header_safe(rendered["subject_en"]))
        sections.append(("en", rendered["body_en"]))
    html = compose_sections(sections)
    return RenderedMail(
        subject=SUBJECT_SEPARATOR.join(subjects),
        html=html,
        text=html_to_plain_text(html),
    )
