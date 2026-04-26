from uuid import UUID

from pydantic import BaseModel, EmailStr


class CreateCompanyRequest(BaseModel):
    name: str


class UpdateCompanyRequest(BaseModel):
    name: str


class KpCompanyProfileResponse(BaseModel):
    id: UUID
    company_id: UUID
    invoice_address: str
    shipping_address: str
    contact_email: EmailStr | None
    kp_contact_user_id: UUID | None


class UpdateKpCompanyProfileRequest(BaseModel):
    invoice_address: str
    shipping_address: str
    contact_email: EmailStr | None = None
    kp_contact_user_id: UUID | None = None


class SetupCompanyRequest(BaseModel):
    name: str


class CreateInviteRequest(BaseModel):
    email: EmailStr


class InviteInfoResponse(BaseModel):
    company_name: str


class CompanyAssignedUserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    user_confirmed: bool
    email_confirmed: bool


class CompanyWithUsersResponse(BaseModel):
    id: UUID
    name: str
    users: list[CompanyAssignedUserResponse]
