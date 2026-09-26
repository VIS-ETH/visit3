from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.mail_templates.renderer import MAX_TEMPLATE_CHARACTERS

MAX_SUBJECT_CHARACTERS = 500


class MailTemplateResult(BaseModel):
    key: str
    subject_de: str
    subject_en: str
    body_de: str
    body_en: str
    default_subject_de: str
    default_subject_en: str
    default_body_de: str
    default_body_en: str
    variables: list[str]
    is_customized: bool
    updated_at: datetime | None = None
    updated_by_user_id: UUID | None = None


class MailTemplateResponse(MailTemplateResult):
    pass


class UpdateMailTemplateInput(BaseModel):
    subject_de: str = Field(min_length=1, max_length=MAX_SUBJECT_CHARACTERS)
    subject_en: str = Field(min_length=1, max_length=MAX_SUBJECT_CHARACTERS)
    body_de: str = Field(min_length=1, max_length=MAX_TEMPLATE_CHARACTERS)
    body_en: str = Field(min_length=1, max_length=MAX_TEMPLATE_CHARACTERS)


class UpdateMailTemplateRequest(UpdateMailTemplateInput):
    pass


class MailPreviewResult(BaseModel):
    subject: str
    html: str
    text: str


class MailPreviewResponse(MailPreviewResult):
    pass
