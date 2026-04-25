from uuid import UUID

from app.core.utils import strip_text
from pydantic import BaseModel, EmailStr, Field, field_validator


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
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    phone_number: str | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str) -> str:
        return strip_text(v)


class UpdateUserProfileRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    phone_number: str | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str | None) -> str | None:
        return strip_text(v)


class UpdateCompanyUserRequest(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    phone_number: str | None = None
    company_id: UUID | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str | None) -> str | None:
        return strip_text(v)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class ForgetPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
