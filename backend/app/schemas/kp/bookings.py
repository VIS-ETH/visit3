from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.utils import strip_text
from app.models.company import Company
from app.models.kp_event import MAX_SERVICE_QUANTITY, KpBookingStatus
from app.schemas.company import CompanyResponse
from app.schemas.kp.booth_zones import BoothZoneResponse, StaffBoothZoneResponse
from app.schemas.kp.services import ServiceResponse
from app.schemas.limits import MAX_DB_INT
from app.schemas.pricing import PriceBreakdown

BoothNumber = Annotated[int, Field(ge=1, le=MAX_DB_INT)]


class CreateBookingInput(BaseModel):
    status: KpBookingStatus = KpBookingStatus.REGISTERED
    offer_deadline: date | None = None
    offer_made_on: date | None = None


class OfferBookingRequest(BaseModel):
    company_id: UUID
    booth_zone_id: UUID
    deadline: date


class UpdateBookingOfferRequest(BaseModel):
    deadline: date


class AcceptOfferRequest(BaseModel):
    confirm_profile: bool = False
    accept_terms: bool = False


class UpdateBookingInput(BaseModel):
    status: KpBookingStatus | None = None
    booth_nr: BoothNumber | None = None
    booth_zone_id: UUID | None = None
    status_note: str | None = None
    status_changed_at: datetime | None = None
    rejection_reason: str | None = None
    confirmed_at: datetime | None = None
    reminder_sent_at: datetime | None = None
    offer_deadline: date | None = None
    offer_made_on: date | None = None
    offer_week_reminder_sent_at: datetime | None = None
    offer_day_reminder_sent_at: datetime | None = None


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
    booth_nr: BoothNumber | None = None
    services: list[StaffBookingServiceInput] | None = None
    status_note: str | None = None


class StaffUpdateBookingRequest(StaffUpdateBookingInput):
    pass


class UpdateBookingBoothNumberInput(BaseModel):
    booth_nr: BoothNumber | None = None


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


class BookingAdditionResponse(BaseModel):
    booking_service_id: UUID
    quantity: int


class BookingAdditionalServiceChargeResponse(BaseModel):
    name: str
    quantity: int
    charged_quantity: int
    line_net: int


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
    offer_deadline: date | None = None
    missing_items: list[str] = Field(default_factory=lambda: [])
    is_complete: bool = True


class PricedBookingBase(BookingBase):
    services: list[BookingServiceResponse] = Field(default_factory=lambda: [])
    additional_service_charges: list[BookingAdditionalServiceChargeResponse] = Field(
        default_factory=lambda: []
    )
    price: PriceBreakdown


class BookingResponse(PricedBookingBase):
    booth_zone: BoothZoneResponse | None = None
    net_total: int = 0


class MyBookingResponse(BookingResponse):
    can_register: bool


class BookingWithBoothZoneBase(PricedBookingBase):
    booth_zone: StaffBoothZoneResponse
    net_total: int
    booked_services_count: int
    booked_services_summary: str
    nametag_count: int
    waitlist_count: int
    company_details_submitted: bool
    created_at: datetime | None = None
    changed_at: datetime | None = None
    status_note: str | None = None
    added_after_confirmation: list[BookingAdditionResponse] = Field(
        default_factory=lambda: []
    )


class BookingWithCompanyAndBoothZoneResponse(BookingWithBoothZoneBase):
    company: Company


class StaffBookingResponse(BookingWithBoothZoneBase):
    company: CompanyResponse


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
