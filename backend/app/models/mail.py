from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, String, Text, UniqueConstraint
from sqlmodel import Field

from app.models.base import TIMESTAMPTZ, BaseEntity

STATUS_LENGTH = 32


class MailTemplate(BaseEntity, table=True):
    key: str = Field(index=True, unique=True)
    subject_de: str
    subject_en: str
    body_de: str
    body_en: str
    updated_by_user_id: UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )


class MailCampaignStatus(StrEnum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    SENDING = "SENDING"
    SENT = "SENT"
    PARTIALLY_FAILED = "PARTIALLY_FAILED"


EDITABLE_CAMPAIGN_STATUSES = (MailCampaignStatus.DRAFT, MailCampaignStatus.SCHEDULED)


class MailCampaignSegment(StrEnum):
    ALL = "ALL"
    NOT_REGISTERED = "NOT_REGISTERED"
    REGISTERED = "REGISTERED"
    CONFIRMED = "CONFIRMED"
    OFFERED = "OFFERED"
    WAITLISTED = "WAITLISTED"


class MailCampaignRecipientStatus(StrEnum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class MailCampaignRecipientSource(StrEnum):
    CONTACT = "CONTACT"
    GENERAL_EMAIL = "GENERAL_EMAIL"


class MailCampaignSkipReason(StrEnum):
    NO_ADDRESS = "NO_ADDRESS"
    DUPLICATE_ADDRESS = "DUPLICATE_ADDRESS"


class MailCampaignFailure(StrEnum):
    DELIVERY_FAILED = "DELIVERY_FAILED"
    RENDER_FAILED = "RENDER_FAILED"
    INTERRUPTED = "INTERRUPTED"
    ABORTED = "ABORTED"


class MailCampaign(BaseEntity, table=True):
    name: str
    event_id: UUID = Field(foreign_key="kpevent.id", index=True)
    subject_de: str
    subject_en: str = Field(default="")
    body_de: str = Field(sa_type=Text)
    body_en: str = Field(default="", sa_type=Text)
    audience: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    status: str = Field(
        default=MailCampaignStatus.DRAFT,
        sa_column=Column(String(STATUS_LENGTH), nullable=False, index=True),
    )
    scheduled_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )
    lease_expires_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )
    recipients_resolved_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )
    started_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )
    finished_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )
    created_by_user_id: UUID | None = Field(default=None, foreign_key="user.id")
    updated_by_user_id: UUID | None = Field(default=None, foreign_key="user.id")
    sent_by_user_id: UUID | None = Field(default=None, foreign_key="user.id")


class MailCampaignRecipient(BaseEntity, table=True):
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "company_id",
            name="uq_mailcampaignrecipient_campaign_id_company_id",
        ),
    )

    campaign_id: UUID = Field(foreign_key="mailcampaign.id", index=True)
    company_id: UUID = Field(foreign_key="company.id")
    company_name: str
    email: str | None = Field(default=None)
    source: str | None = Field(
        default=None, sa_column=Column(String(STATUS_LENGTH), nullable=True)
    )
    contact_user_id: UUID | None = Field(default=None, foreign_key="user.id")
    status: str = Field(
        default=MailCampaignRecipientStatus.PENDING,
        sa_column=Column(String(STATUS_LENGTH), nullable=False),
    )
    skip_reason: str | None = Field(
        default=None, sa_column=Column(String(STATUS_LENGTH), nullable=True)
    )
    error: str | None = Field(
        default=None, sa_column=Column(String(STATUS_LENGTH), nullable=True)
    )
    attempts: int = Field(default=0)
    last_attempt_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )
    sent_at: datetime | None = Field(default=None, nullable=True, sa_type=TIMESTAMPTZ)
