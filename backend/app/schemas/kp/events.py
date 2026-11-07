from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.utils import normalize_http_url
from app.models.kp_event import DEFAULT_MAX_NAMETAGS_PER_BOOKING, MAX_SERVICE_QUANTITY
from app.schemas.limits import MAX_REMINDER_DAYS
from app.schemas.pricing import VatRatePercent, percent_to_permille

DEFAULT_VAT_RATE_PERCENT = Decimal("8.1")
DEFAULT_FINALIZATION_REMINDER_DAYS = 3
MAX_VAT_RATE_PERCENT = 100


class CreateKpInput(BaseModel):
    name: str
    registration_open: date
    registration_end: date
    finalization_deadline: date
    nametags_deadline: date
    event_date: date
    vat_rate_percent: VatRatePercent = Field(
        default=DEFAULT_VAT_RATE_PERCENT,
        ge=0,
        le=MAX_VAT_RATE_PERCENT,
        decimal_places=1,
    )
    terms_url: str | None = None
    notification_email: EmailStr | None = None
    finalization_reminder_days: int = Field(
        default=DEFAULT_FINALIZATION_REMINDER_DAYS, ge=0, le=MAX_REMINDER_DAYS
    )
    max_nametags_per_booking: int = Field(
        default=DEFAULT_MAX_NAMETAGS_PER_BOOKING, ge=1, le=MAX_SERVICE_QUANTITY
    )

    @field_validator("terms_url")
    @classmethod
    def validate_terms_url(cls, value: str | None) -> str | None:
        return normalize_http_url(value)


class CreateKpRequest(CreateKpInput):
    pass


class CloneKpInput(CreateKpInput):
    pass


class CloneKpRequest(CloneKpInput):
    pass


class UpdateKpInput(BaseModel):
    name: str | None = None
    registration_open: date | None = None
    registration_end: date | None = None
    finalization_deadline: date | None = None
    nametags_deadline: date | None = None
    event_date: date | None = None
    vat_rate_percent: VatRatePercent | None = Field(
        default=None, ge=0, le=MAX_VAT_RATE_PERCENT, decimal_places=1
    )
    terms_url: str | None = None
    notification_email: EmailStr | None = None
    finalization_reminder_days: int | None = Field(
        default=None, ge=0, le=MAX_REMINDER_DAYS
    )
    max_nametags_per_booking: int | None = Field(
        default=None, ge=1, le=MAX_SERVICE_QUANTITY
    )

    @field_validator("terms_url")
    @classmethod
    def validate_terms_url(cls, value: str | None) -> str | None:
        return normalize_http_url(value)


class UpdateKpRequest(UpdateKpInput):
    pass


def kp_event_columns(values: dict[str, Any]) -> dict[str, Any]:
    percent = values.pop("vat_rate_percent", None)
    if percent is not None:
        values["vat_rate_permille"] = percent_to_permille(percent)
    return values


class KpResponse(BaseModel):
    id: UUID
    name: str
    registration_open: date
    registration_end: date
    finalization_deadline: date
    nametags_deadline: date
    event_date: date
    vat_rate_percent: VatRatePercent
    terms_url: str | None
    finalization_reminder_days: int
    max_nametags_per_booking: int


class EventBannerSource(BaseModel):
    width: int
    url: str


class EventBannerResult(BaseModel):
    width: int
    height: int
    sources: list[EventBannerSource]


class EventBannerResponse(EventBannerResult):
    pass


class KpLatestResult(KpResponse):
    model_config = ConfigDict(from_attributes=True)

    banner: EventBannerResponse | None = None


class KpLatestResponse(KpLatestResult):
    pass


class KpStaffResponse(KpResponse):
    notification_email: EmailStr | None
