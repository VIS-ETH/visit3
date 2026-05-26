from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.company import Company
from app.models.kp_event import (
    KpBookingStatus,
    KpCompanyLanguage,
    KpEventServiceRequirementType,
)


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


class UpdateKpRequest(UpdateKpInput):
    pass


class KpResponse(BaseModel):
    id: UUID
    name: str
    registration_open: date
    registration_end: date
    finalization_deadline: date
    nametags_deadline: date
    event_date: date


# --- Booth Zones ---


class CreateBoothZoneInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    color: str = "#000000"
    order: int = Field(default=100, ge=0)
    capacity: int = Field(default=0, ge=0)
    booth_size: float = Field(default=0, ge=0)
    base_price: int = Field(default=0, ge=0)


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


class UpdateBoothZoneRequest(UpdateBoothZoneInput):
    pass


class BoothZoneResponse(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    description: str
    color: str
    order: int
    capacity: int
    booth_size: float
    base_price: int


# --- Services ---


class ServiceRequirementInput(BaseModel):
    id: UUID | None = None
    type: KpEventServiceRequirementType
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=20)
    order: int = Field(default=100, ge=0)


class CreateServiceInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    confirmation_description: str | None = None
    order: int = Field(default=100, ge=0)
    price: int = Field(default=0, ge=0)
    max_quantity_per_booking: int = Field(default=1, ge=1)
    max_total_quantity: int = Field(default=0, ge=0)
    is_active: bool = True
    requirements: list[ServiceRequirementInput] = []


class CreateServiceRequest(CreateServiceInput):
    pass


class UpdateServiceInput(BaseModel):
    name: str | None = None
    description: str | None = None
    confirmation_description: str | None = None
    order: int | None = Field(default=None, ge=0)
    price: int | None = Field(default=None, ge=0)
    max_quantity_per_booking: int | None = Field(default=None, ge=1)
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
    image_url: str | None
    confirmation_description: str | None
    order: int
    price: int
    max_quantity_per_booking: int
    max_total_quantity: int
    is_active: bool
    requirements: list[ServiceRequirementResponse]


# --- Industries ---


class CreateIndustryInput(BaseModel):
    name: str = Field(min_length=1)


class CreateIndustryRequest(CreateIndustryInput):
    pass


class IndustryResponse(BaseModel):
    id: UUID
    name: str


# --- Bookings ---


class CreateBookingInput(BaseModel):
    status: KpBookingStatus = KpBookingStatus.REGISTERED


class UpdateBookingInput(BaseModel):
    status: KpBookingStatus | None = None
    booth_nr: int | None = Field(default=None, ge=1)


class UpdateBookingStatusInput(BaseModel):
    status: KpBookingStatus


class UpdateBookingStatusRequest(UpdateBookingStatusInput):
    pass


class UpdateBookingBoothNumberInput(BaseModel):
    booth_nr: int | None = Field(default=None, ge=1)


class UpdateBookingBoothNumberRequest(UpdateBookingBoothNumberInput):
    pass


class BookingServiceInput(BaseModel):
    service_id: UUID
    quantity: int = Field(ge=1)


class UpsertCompanyDetailsInput(BaseModel):
    profile: str | None = None
    brand_name: str | None = None
    address: str | None = None
    contact_person: str | None = None
    places_of_work: str | None = None
    employees_count: int | None = Field(default=None, ge=0)
    employees_count_switzerland: int | None = Field(default=None, ge=0)
    offer_internship: bool | None = None
    offer_part_time: bool | None = None
    offer_thesis: bool | None = None
    languages: list[KpCompanyLanguage] | None = None


class ReplaceBookingUpgradeWaitlistRequest(BaseModel):
    target_booth_zone_ids: list[UUID]


class RegisterBookingRequest(BaseModel):
    booth_zone_id: UUID
    services: list[BookingServiceInput] = Field(default_factory=lambda: [])


class BookingServiceResponse(BaseModel):
    id: UUID
    booking_id: UUID
    service_id: UUID
    quantity: int
    included_quantity: int
    service: ServiceResponse


class BoothZoneWithAvailabilityResult(BoothZoneResponse):
    available_spots: int


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


class BookingResponse(BookingBase):
    booth_zone: BoothZoneResponse | None = None
    services: list[BookingServiceResponse] = Field(default_factory=lambda: [])


class BookingWithCompanyAndBoothZoneResponse(BookingBase):
    company: Company
    booth_zone: BoothZoneResponse
    total_price: int
    booked_services_count: int
    booked_services_summary: str
    nametag_count: int
    waitlist_count: int
    company_details_submitted: bool


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


class ExportBackgroundResponse(BaseModel):
    id: UUID
    event_id: UUID
    created_at: datetime
    updated_at: datetime
    stored_file: StoredFileResponse


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


class BookingUpgradeWaitlistEntryResponse(BaseModel):
    id: UUID
    booking_id: UUID
    target_booth_zone_id: UUID
    priority_rank: int | None
    target_booth_zone: BoothZoneResponse
