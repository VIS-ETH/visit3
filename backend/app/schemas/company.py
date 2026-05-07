from uuid import UUID

from pydantic import BaseModel, EmailStr


class CreateCompanyInput(BaseModel):
    name: str


class CreateCompanyRequest(CreateCompanyInput):
    pass


class UpdateCompanyInput(BaseModel):
    name: str


class UpdateCompanyRequest(UpdateCompanyInput):
    pass


class KpCompanyProfileResult(BaseModel):
    id: UUID
    company_id: UUID
    invoice_address: str
    shipping_address: str
    contact_email: EmailStr | None
    kp_contact_user_id: UUID | None


class KpCompanyProfileResponse(KpCompanyProfileResult):
    pass


class UpdateKpCompanyProfileInput(BaseModel):
    invoice_address: str
    shipping_address: str
    contact_email: EmailStr | None = None
    kp_contact_user_id: UUID | None = None


class UpdateKpCompanyProfileRequest(UpdateKpCompanyProfileInput):
    pass


class SetupCompanyInput(BaseModel):
    name: str


class SetupCompanyRequest(SetupCompanyInput):
    pass


class CreateInviteInput(BaseModel):
    email: EmailStr


class CreateInviteRequest(CreateInviteInput):
    pass


class InviteInfoResult(BaseModel):
    company_name: str


class InviteInfoResponse(InviteInfoResult):
    pass


class CompanyAssignedUserResult(BaseModel):
    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    user_confirmed: bool
    email_confirmed: bool


class CompanyAssignedUserResponse(CompanyAssignedUserResult):
    pass


class CompanyWithUsersResult(BaseModel):
    id: UUID
    name: str
    users: list[CompanyAssignedUserResult]


class CompanyWithUsersResponse(CompanyWithUsersResult):
    users: list[CompanyAssignedUserResponse]
