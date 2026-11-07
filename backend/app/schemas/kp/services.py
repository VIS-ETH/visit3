from uuid import UUID

from pydantic import BaseModel, Field

from app.models.kp_event import (
    MAX_SERVICE_QUANTITY,
    KpEventServiceRequirementType,
    KpServiceCategory,
)
from app.schemas.kp.booth_zones import IncludedServiceInput, IncludedServiceResponse
from app.schemas.limits import MAX_DB_INT


class ServiceRequirementInput(BaseModel):
    id: UUID | None = None
    type: KpEventServiceRequirementType
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=20)
    order: int = Field(default=100, ge=0, le=MAX_DB_INT)


class CreateServiceInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    category: KpServiceCategory = KpServiceCategory.SERVICE
    unit_label: str | None = None
    confirmation_description: str | None = None
    order: int = Field(default=100, ge=0, le=MAX_DB_INT)
    price: int = Field(default=0, ge=0, le=MAX_DB_INT)
    max_quantity_per_booking: int = Field(default=1, ge=1, le=MAX_SERVICE_QUANTITY)
    max_total_quantity: int = Field(default=0, ge=0, le=MAX_DB_INT)
    is_active: bool = True
    requirements: list[ServiceRequirementInput] = []
    included_services: list[IncludedServiceInput] = []
    excluded_service_ids: list[UUID] = []


class CreateServiceRequest(CreateServiceInput):
    pass


class UpdateServiceInput(BaseModel):
    name: str | None = None
    description: str | None = None
    category: KpServiceCategory | None = None
    unit_label: str | None = None
    confirmation_description: str | None = None
    order: int | None = Field(default=None, ge=0, le=MAX_DB_INT)
    price: int | None = Field(default=None, ge=0, le=MAX_DB_INT)
    max_quantity_per_booking: int | None = Field(
        default=None, ge=1, le=MAX_SERVICE_QUANTITY
    )
    max_total_quantity: int | None = Field(default=None, ge=0, le=MAX_DB_INT)
    is_active: bool | None = None
    requirements: list[ServiceRequirementInput] | None = None
    included_services: list[IncludedServiceInput] | None = None
    excluded_service_ids: list[UUID] | None = None


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
    included_services: list[IncludedServiceResponse] = []
    excluded_service_ids: list[UUID] = []
