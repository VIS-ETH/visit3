from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.utils import normalize_http_url, strip_text
from app.models.company import Company
from app.models.kp_event import (
    DEFAULT_MAX_NAMETAGS_PER_BOOKING,
    LAYOUT_DESCRIPTION_MAX_LENGTH,
    MAX_SERVICE_QUANTITY,
    KpBookingStatus,
    KpEventServiceRequirementType,
    KpServiceCategory,
)
from app.schemas.company import CompanyResponse
from app.schemas.pricing import PriceBreakdown, VatRatePercent, percent_to_permille

DEFAULT_VAT_RATE_PERCENT = Decimal("8.1")
DEFAULT_FINALIZATION_REMINDER_DAYS = 3
MAX_VAT_RATE_PERCENT = 100


class StoredFileResponse(BaseModel):
    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    etag: str | None
    created_at: datetime
    updated_at: datetime


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
        default=DEFAULT_FINALIZATION_REMINDER_DAYS, ge=0
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
    finalization_reminder_days: int | None = Field(default=None, ge=0)
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


class KpStaffResponse(KpResponse):
    notification_email: EmailStr | None


class IncludedServiceInput(BaseModel):
    service_id: UUID
    included_quantity: int = Field(default=1, ge=1, le=MAX_SERVICE_QUANTITY)


class CreateBoothZoneInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    color: str = "#000000"
    order: int = Field(default=100, ge=0)
    capacity: int = Field(default=0, ge=0)
    booth_size: float = Field(default=0, ge=0)
    base_price: int = Field(default=0, ge=0)
    layout_description: str | None = Field(
        default=None, max_length=LAYOUT_DESCRIPTION_MAX_LENGTH
    )
    included_services: list[IncludedServiceInput] = Field(default_factory=lambda: [])


class CreateBoothZoneRequest(CreateBoothZoneInput):
    pass


class UpdateBoothZoneInput(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    order: int | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, ge=0)
    booth_size: float | None = Field(default=None, ge=0)
    base_price: int | None = Field(default=None, ge=0)
    layout_description: str | None = Field(
        default=None, max_length=LAYOUT_DESCRIPTION_MAX_LENGTH
    )
    included_services: list[IncludedServiceInput] | None = None


class UpdateBoothZoneRequest(UpdateBoothZoneInput):
    pass


class IncludedServiceResponse(BaseModel):
    service_id: UUID
    included_quantity: int


class BoothZoneResponse(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    description: str
    color: str
    order: int
    booth_size: float
    base_price: int
    layout_description: str | None = None
    layout_url: str | None = None
    included_services: list[IncludedServiceResponse]


class StaffBoothZoneResponse(BoothZoneResponse):
    capacity: int


class ServiceRequirementInput(BaseModel):
    id: UUID | None = None
    type: KpEventServiceRequirementType
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=20)
    order: int = Field(default=100, ge=0)


class CreateServiceInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    category: KpServiceCategory = KpServiceCategory.SERVICE
    unit_label: str | None = None
    confirmation_description: str | None = None
    order: int = Field(default=100, ge=0)
    price: int = Field(default=0, ge=0)
    max_quantity_per_booking: int = Field(default=1, ge=1, le=MAX_SERVICE_QUANTITY)
    max_total_quantity: int = Field(default=0, ge=0)
    is_active: bool = True
    requirements: list[ServiceRequirementInput] = []


class CreateServiceRequest(CreateServiceInput):
    pass


class UpdateServiceInput(BaseModel):
    name: str | None = None
    description: str | None = None
    category: KpServiceCategory | None = None
    unit_label: str | None = None
    confirmation_description: str | None = None
    order: int | None = Field(default=None, ge=0)
    price: int | None = Field(default=None, ge=0)
    max_quantity_per_booking: int | None = Field(
        default=None, ge=1, le=MAX_SERVICE_QUANTITY
    )
    max_total_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    requirements: list[ServiceRequirementInput] | None = None


class UpdateServiceRequest(UpdateServiceInput):
    pass


class ServiceRequirementResponse(BaseModel):
    id: UUID
    service_id: UUID
    type: KpEventServiceRequirementType
    name: str
    description: str
    order: int


class ServiceResponse(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    description: str
    category: KpServiceCategory
    unit_label: str | None
    image_url: str | None = None
    confirmation_description: str | None
    order: int
    price: int
    max_quantity_per_booking: int
    max_total_quantity: int
    remaining_total_quantity: int | None = None
    is_active: bool
    requirements: list[ServiceRequirementResponse]


class CreateBookingInput(BaseModel):
    status: KpBookingStatus = KpBookingStatus.REGISTERED


class UpdateBookingInput(BaseModel):
    status: KpBookingStatus | None = None
    booth_nr: int | None = Field(default=None, ge=1)
    booth_zone_id: UUID | None = None
    status_note: str | None = None
    status_changed_at: datetime | None = None
    rejection_reason: str | None = None
    confirmed_at: datetime | None = None
    reminder_sent_at: datetime | None = None


class UpdateBookingStatusInput(BaseModel):
    status: KpBookingStatus


class UpdateBookingStatusRequest(UpdateBookingStatusInput):
    pass


class RejectBookingInput(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return strip_text(value)


class RejectBookingRequest(RejectBookingInput):
    pass


class StaffBookingServiceInput(BaseModel):
    service_id: UUID
    quantity: int = Field(ge=0, le=MAX_SERVICE_QUANTITY)


class StaffUpdateBookingInput(BaseModel):
    booth_zone_id: UUID | None = None
    booth_nr: int | None = Field(default=None, ge=1)
    services: list[StaffBookingServiceInput] | None = None
    status_note: str | None = None


class StaffUpdateBookingRequest(StaffUpdateBookingInput):
    pass


class UpdateBookingBoothNumberInput(BaseModel):
    booth_nr: int | None = Field(default=None, ge=1)


class UpdateBookingBoothNumberRequest(UpdateBookingBoothNumberInput):
    pass


class BookingServiceInput(BaseModel):
    service_id: UUID
    quantity: int = Field(ge=1, le=MAX_SERVICE_QUANTITY)


class ReplaceBookingUpgradeWaitlistRequest(BaseModel):
    target_booth_zone_ids: list[UUID]


class SwitchBookingZoneInput(BaseModel):
    booth_zone_id: UUID


class SwitchBookingZoneRequest(SwitchBookingZoneInput):
    pass


class RegisterBookingRequest(BaseModel):
    booth_zone_id: UUID
    services: list[BookingServiceInput] = Field(default_factory=lambda: [])
    confirm_profile: bool = False


class AddBookingServicesRequest(BaseModel):
    services: list[BookingServiceInput] = Field(default_factory=lambda: [])


class BookingServiceResponse(BaseModel):
    id: UUID
    booking_id: UUID
    service_id: UUID
    quantity: int
    included_quantity: int
    charged_quantity: int
    unit_price: int
    line_net: int
    service: ServiceResponse


class BookingAdditionalServiceChargeResponse(BaseModel):
    name: str
    quantity: int
    charged_quantity: int
    line_net: int


class BoothZoneWithAvailabilityResult(BoothZoneResponse):
    is_full: bool


class BoothZoneWithAvailabilityResponse(BoothZoneWithAvailabilityResult):
    pass


class BookingBase(BaseModel):
    id: UUID
    booking_number: int
    event_id: UUID
    company_id: UUID
    booth_zone_id: UUID
    booth_nr: int | None
    status: KpBookingStatus
    status_changed_at: datetime | None = None
    confirmed_at: datetime | None = None
    rejection_reason: str | None = None
    missing_items: list[str] = Field(default_factory=lambda: [])
    is_complete: bool = True


class BookingResponse(BookingBase):
    booth_zone: BoothZoneResponse | None = None
    services: list[BookingServiceResponse] = Field(default_factory=lambda: [])
    additional_service_charges: list[BookingAdditionalServiceChargeResponse] = Field(
        default_factory=lambda: []
    )
    net_total: int = 0
    price: PriceBreakdown


class MyBookingResponse(BookingResponse):
    can_register: bool


class BookingWithBoothZoneBase(BookingBase):
    booth_zone: StaffBoothZoneResponse
    services: list[BookingServiceResponse] = Field(default_factory=lambda: [])
    additional_service_charges: list[BookingAdditionalServiceChargeResponse] = Field(
        default_factory=lambda: []
    )
    net_total: int
    price: PriceBreakdown
    booked_services_count: int
    booked_services_summary: str
    nametag_count: int
    waitlist_count: int
    company_details_submitted: bool
    status_note: str | None = None


class BookingWithCompanyAndBoothZoneResponse(BookingWithBoothZoneBase):
    company: Company


class StaffBookingResponse(BookingWithBoothZoneBase):
    company: CompanyResponse


class RequirementFileResponse(BaseModel):
    id: UUID
    booking_service_id: UUID
    requirement_id: UUID
    stored_file: StoredFileResponse


class RequirementTextRequest(BaseModel):
    text_value: str = Field(min_length=1)


class RequirementTextResponse(BaseModel):
    id: UUID
    booking_service_id: UUID
    requirement_id: UUID
    text_value: str


class RequirementFileDownloadResponse(BaseModel):
    url: str


class BookingRequirementFileMapResponse(BaseModel):
    files: dict[UUID, RequirementFileResponse]


class ExportBackgroundResponse(BaseModel):
    id: UUID
    event_id: UUID
    created_at: datetime
    updated_at: datetime
    stored_file: StoredFileResponse


class NameTagInput(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    position: str = Field(min_length=1)


class ReplaceNameTagsInput(BaseModel):
    name_tags: list[NameTagInput] = Field(default_factory=lambda: [])


class ReplaceNameTagsRequest(ReplaceNameTagsInput):
    pass


class NameTagResult(BaseModel):
    id: UUID
    booking_id: UUID
    first_name: str
    last_name: str
    position: str


class NameTagResponse(NameTagResult):
    pass


class NametagExportPersonResult(BaseModel):
    id: UUID
    booking_id: UUID
    company_name: str
    first_name: str
    last_name: str
    position: str


class NametagExportPersonResponse(NametagExportPersonResult):
    pass


class NametagExportCompanyResult(BaseModel):
    booking_id: UUID
    company_id: UUID
    company_name: str
    booth_zone_name: str
    booth_nr: int | None
    nametag_count: int


class NametagExportCompanyResponse(NametagExportCompanyResult):
    pass


class NametagExportTargetsResult(BaseModel):
    companies: list[NametagExportCompanyResult]
    people: list[NametagExportPersonResult]


class NametagExportTargetsResponse(NametagExportTargetsResult):
    pass


class BookingUpgradeWaitlistEntryBase(BaseModel):
    id: UUID
    booking_id: UUID
    target_booth_zone_id: UUID
    priority_rank: int | None
    is_full: bool
    position: int


class BookingUpgradeWaitlistEntryResult(BookingUpgradeWaitlistEntryBase):
    target_booth_zone: BoothZoneResponse


class BookingUpgradeWaitlistEntryResponse(BookingUpgradeWaitlistEntryResult):
    pass


class StaffBookingUpgradeWaitlistEntryResult(BookingUpgradeWaitlistEntryBase):
    target_booth_zone: StaffBoothZoneResponse
    available_spots: int


class StaffBookingUpgradeWaitlistEntryResponse(StaffBookingUpgradeWaitlistEntryResult):
    pass
