from datetime import datetime, timezone
from typing import Annotated, Self
from uuid import UUID

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, model_validator

from app.core.utils import reject_control_characters, strip_text
from app.mail_templates.renderer import MAX_TEMPLATE_CHARACTERS
from app.mail_templates.texts import MailTemplateTexts
from app.models.mail import (
    MailCampaignFailure,
    MailCampaignRecipientSource,
    MailCampaignRecipientStatus,
    MailCampaignSegment,
    MailCampaignSkipReason,
    MailCampaignStatus,
)
from app.schemas.mail import MAX_SUBJECT_CHARACTERS

MAX_CAMPAIGN_NAME_CHARACTERS = 200
MAX_AUDIENCE_ZONES = 100
MAX_AUDIENCE_COMPANIES = 2000


def _strip(value: object) -> object:
    return strip_text(value) if isinstance(value, str) else value


def _unique[T](values: list[T]) -> list[T]:
    return list(dict.fromkeys(values))


def _assume_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(_assume_utc)]

CampaignName = Annotated[
    str,
    Field(min_length=1, max_length=MAX_CAMPAIGN_NAME_CHARACTERS),
    BeforeValidator(_strip),
    AfterValidator(reject_control_characters),
]
CampaignSubject = Annotated[
    str,
    Field(max_length=MAX_SUBJECT_CHARACTERS),
    BeforeValidator(_strip),
    AfterValidator(reject_control_characters),
]
CampaignBody = Annotated[str, Field(max_length=MAX_TEMPLATE_CHARACTERS)]


class MailCampaignAudience(BaseModel):
    segments: Annotated[list[MailCampaignSegment], AfterValidator(_unique)] = Field(
        default_factory=list[MailCampaignSegment], max_length=len(MailCampaignSegment)
    )
    booth_zone_ids: Annotated[list[UUID], AfterValidator(_unique)] = Field(
        default_factory=list[UUID], max_length=MAX_AUDIENCE_ZONES
    )
    include_company_ids: Annotated[list[UUID], AfterValidator(_unique)] = Field(
        default_factory=list[UUID], max_length=MAX_AUDIENCE_COMPANIES
    )
    exclude_company_ids: Annotated[list[UUID], AfterValidator(_unique)] = Field(
        default_factory=list[UUID], max_length=MAX_AUDIENCE_COMPANIES
    )

    @model_validator(mode="after")
    def validate_manual_lists(self) -> Self:
        if set(self.include_company_ids) & set(self.exclude_company_ids):
            raise ValueError("a company cannot be included and excluded")
        return self


class MailCampaignTextsInput(BaseModel):
    subject_de: CampaignSubject = Field(min_length=1)
    subject_en: CampaignSubject = ""
    body_de: CampaignBody = Field(min_length=1)
    body_en: CampaignBody = ""

    @model_validator(mode="after")
    def validate_english_pair(self) -> Self:
        if bool(self.subject_en) != bool(self.body_en.strip()):
            raise ValueError("the English subject and body must be set together")
        if not self.body_de.strip():
            raise ValueError("the German body must not be blank")
        return self

    def texts(self) -> MailTemplateTexts:
        return MailTemplateTexts(
            subject_de=self.subject_de,
            subject_en=self.subject_en,
            body_de=self.body_de,
            body_en=self.body_en,
        )


class MailCampaignInput(MailCampaignTextsInput):
    name: CampaignName
    event_id: UUID
    audience: MailCampaignAudience = Field(default_factory=MailCampaignAudience)


class MailCampaignRequest(MailCampaignInput):
    pass


class MailCampaignAudienceInput(BaseModel):
    event_id: UUID
    audience: MailCampaignAudience


class MailCampaignAudienceRequest(MailCampaignAudienceInput):
    pass


class MailCampaignRenderInput(MailCampaignTextsInput):
    event_id: UUID
    company_id: UUID | None = None


class MailCampaignRenderRequest(MailCampaignRenderInput):
    pass


class MailCampaignScheduleInput(BaseModel):
    scheduled_at: datetime


class MailCampaignScheduleRequest(MailCampaignScheduleInput):
    pass


class MailCampaignRecipientPreviewResult(BaseModel):
    company_id: UUID
    company_name: str
    email: str | None
    source: MailCampaignRecipientSource | None
    skip_reason: MailCampaignSkipReason | None
    manually_included: bool


class MailCampaignAudienceResult(BaseModel):
    recipient_count: int
    skipped_count: int
    recipients: list[MailCampaignRecipientPreviewResult]


class MailCampaignAudienceResponse(MailCampaignAudienceResult):
    pass


class MailCampaignCounts(BaseModel):
    pending: int = 0
    sent: int = 0
    failed: int = 0
    skipped: int = 0


class MailCampaignSummaryResult(BaseModel):
    id: UUID
    name: str
    event_id: UUID
    event_name: str
    status: MailCampaignStatus
    scheduled_at: UtcDatetime | None
    started_at: UtcDatetime | None
    finished_at: UtcDatetime | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    counts: MailCampaignCounts


class MailCampaignSummaryResponse(MailCampaignSummaryResult):
    pass


class MailCampaignRecipientResult(BaseModel):
    id: UUID
    company_id: UUID
    company_name: str
    email: str | None
    source: MailCampaignRecipientSource | None
    status: MailCampaignRecipientStatus
    skip_reason: MailCampaignSkipReason | None
    error: MailCampaignFailure | None
    attempts: int
    last_attempt_at: UtcDatetime | None
    sent_at: UtcDatetime | None


class MailCampaignResult(MailCampaignSummaryResult):
    subject_de: str
    subject_en: str
    body_de: str
    body_en: str
    audience: MailCampaignAudience
    recipients: list[MailCampaignRecipientResult]


class MailCampaignResponse(MailCampaignResult):
    pass


class MailCampaignCompanyResult(BaseModel):
    id: UUID
    name: str


class MailCampaignCompanyResponse(MailCampaignCompanyResult):
    pass
