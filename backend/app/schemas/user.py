from uuid import UUID

from pydantic import BaseModel


class CompanyResponse(BaseModel):
    id: UUID
    name: str


class CompanyUserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    user_confirmed: bool
    email_confirmed: bool
    company: CompanyResponse | None = None


class RegisterUserRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    phone_number: str | None = None


class UpdateUserProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None


class UpdateCompanyUserRequest(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    company_id: UUID | None = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class ForgetPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
