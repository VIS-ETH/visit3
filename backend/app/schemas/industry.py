from uuid import UUID

from pydantic import BaseModel, Field


class IndustryResult(BaseModel):
    id: UUID
    name: str


class IndustryResponse(IndustryResult):
    pass


class CreateIndustryInput(BaseModel):
    name: str = Field(min_length=1)


class CreateIndustryRequest(CreateIndustryInput):
    pass


class UpdateIndustryInput(BaseModel):
    name: str = Field(min_length=1)


class UpdateIndustryRequest(UpdateIndustryInput):
    pass
