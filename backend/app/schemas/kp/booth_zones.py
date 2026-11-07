from uuid import UUID

from pydantic import BaseModel, Field

from app.models.kp_event import LAYOUT_DESCRIPTION_MAX_LENGTH, MAX_SERVICE_QUANTITY
from app.schemas.limits import MAX_DB_INT


class IncludedServiceInput(BaseModel):
    service_id: UUID
    included_quantity: int = Field(default=1, ge=1, le=MAX_SERVICE_QUANTITY)


class CreateBoothZoneInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    color: str = "#000000"
    order: int = Field(default=100, ge=0, le=MAX_DB_INT)
    capacity: int = Field(default=0, ge=0, le=MAX_DB_INT)
    booth_size: float = Field(default=0, ge=0)
    base_price: int = Field(default=0, ge=0, le=MAX_DB_INT)
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
    order: int | None = Field(default=None, ge=0, le=MAX_DB_INT)
    capacity: int | None = Field(default=None, ge=0, le=MAX_DB_INT)
    booth_size: float | None = Field(default=None, ge=0)
    base_price: int | None = Field(default=None, ge=0, le=MAX_DB_INT)
    registration_open: bool | None = None
    layout_description: str | None = Field(
        default=None, max_length=LAYOUT_DESCRIPTION_MAX_LENGTH
    )
    included_services: list[IncludedServiceInput] | None = None


class UpdateBoothZoneRequest(UpdateBoothZoneInput):
    pass


class ReorderBoothZonesRequest(BaseModel):
    booth_zone_ids: list[UUID]


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
    registration_open: bool
    layout_description: str | None = None
    layout_url: str | None = None
    included_services: list[IncludedServiceResponse]


class StaffBoothZoneResponse(BoothZoneResponse):
    capacity: int


class BoothZoneWithAvailabilityResult(BoothZoneResponse):
    is_full: bool


class BoothZoneWithAvailabilityResponse(BoothZoneWithAvailabilityResult):
    pass
