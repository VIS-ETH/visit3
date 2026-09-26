from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.company import (
    PROFILE_DESCRIPTION_MAX_LENGTH,
    KpCompanyLanguage,
    normalize_country_code,
)
from app.schemas.industry import IndustryResult


class CreateCompanyInput(BaseModel):
    name: str


class CreateCompanyRequest(CreateCompanyInput):
    pass


class UpdateCompanyInput(BaseModel):
    name: str


class UpdateCompanyRequest(UpdateCompanyInput):
    pass


class CompanyProfileFields(BaseModel):
    description: str = Field(default="", max_length=PROFILE_DESCRIPTION_MAX_LENGTH)
    website: str | None = None
    brand_name: str = ""
    general_email: EmailStr | None = None
    general_phone: str | None = None
    places_of_work: str = ""
    employee_count_switzerland: int | None = Field(default=None, ge=0)
    employee_count_worldwide: int | None = Field(default=None, ge=0)
    offers_internships: bool = False
    offers_part_time: bool = False
    offers_theses: bool = False
    offers_graduate_positions: bool = False
    languages: list[KpCompanyLanguage] = Field(default_factory=lambda: [])
    billing_company_name: str = ""
    billing_street: str = ""
    billing_house_number: str = ""
    billing_postal_code: str = ""
    billing_city: str = ""
    billing_country: str = ""
    billing_vat_number: str | None = None
    billing_email: EmailStr | None = None


class UpdateCompanyProfileInput(CompanyProfileFields):
    kp_contact_user_id: UUID | None = None
    industry_ids: list[UUID] = Field(default_factory=lambda: [])

    @field_validator("billing_country")
    @classmethod
    def validate_billing_country(cls, value: str) -> str:
        return normalize_country_code(value)


class UpdateCompanyProfileRequest(UpdateCompanyProfileInput):
    pass


class CompanyMemberResult(BaseModel):
    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None


class CompanyProfileResult(CompanyProfileFields):
    id: UUID | None = None
    company_id: UUID
    logo_url: str | None = None
    kp_contact_user_id: UUID | None = None
    kp_contact_user: CompanyMemberResult | None = None
    industries: list[IndustryResult] = Field(default_factory=lambda: [])
    profile_completed_at: datetime | None = None
    profile_complete: bool = False
    missing_profile_fields: list[str] = Field(default_factory=lambda: [])


class CompanyProfileResponse(CompanyProfileResult):
    pass


class SetupCompanyInput(BaseModel):
    name: str


class SetupCompanyRequest(SetupCompanyInput):
    pass


class CreateInviteInput(BaseModel):
    email: EmailStr


class CreateInviteRequest(CreateInviteInput):
    pass


class AddCompanyMemberInput(BaseModel):
    user_id: UUID


class AddCompanyMemberRequest(AddCompanyMemberInput):
    pass


class InviteInfoResult(BaseModel):
    company_name: str
    account_exists: bool


class InviteInfoResponse(InviteInfoResult):
    pass


class CompanyAssignedUserResult(CompanyMemberResult):
    user_confirmed: bool
    email_confirmed: bool


class CompanyAssignedUserResponse(CompanyAssignedUserResult):
    pass


class CompanyBase(BaseModel):
    id: UUID
    name: str


class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)


class MyCompanyResult(CompanyBase):
    profile_complete: bool
    profile_bookable: bool
    missing_profile_fields: list[str]


class MyCompanyResponse(MyCompanyResult):
    pass


class CompanyListResult(CompanyBase):
    users_count: int
    bookings_count: int


class CompanyListResponse(CompanyListResult):
    pass


class CompanyPageResult(BaseModel):
    items: list[CompanyListResult]
    total: int
    page: int
    page_size: int


class CompanyPageResponse(CompanyPageResult):
    pass


class CompanyWithUsersResult(CompanyBase):
    users: list[CompanyAssignedUserResult]


class CompanyWithUsersResponse(CompanyWithUsersResult):
    pass


class BookletPageResult(BaseModel):
    png_base64: str
    overflow: bool


class BookletPageResponse(BookletPageResult):
    pass
