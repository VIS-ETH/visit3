from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.utils import strip_text


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    is_staff: bool
    is_admin: bool
    is_company: bool
    is_kp_president: bool
    user_confirmed: bool
    email_confirmed: bool
    company_id: UUID | None = None
    company: CompanyResponse | None = None


class UserFilter(StrEnum):
    ALL = "all"
    UNCONFIRMED = "unconfirmed"
    COMPANY = "company"
    STAFF = "staff"


class UserPageResult(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class UserPageResponse(UserPageResult):
    pass


class RegisterUserInput(BaseModel):
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    phone_number: str | None = None
    invite_token: str | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str) -> str:
        return strip_text(v)


class RegisterUserRequest(RegisterUserInput):
    pass


class UserProfileFieldsInput(BaseModel):
    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    phone_number: str | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str | None) -> str | None:
        return strip_text(v)


class UpdateUserProfileInput(UserProfileFieldsInput):
    pass


class UpdateUserProfileRequest(UpdateUserProfileInput):
    pass


class UpdateCompanyUserInput(UserProfileFieldsInput):
    email: EmailStr | None = None
    company_id: UUID | None = None
    user_confirmed: bool | None = None
    is_staff: bool | None = None
    is_admin: bool | None = None

    @field_validator("user_confirmed", "is_staff", "is_admin")
    @classmethod
    def flag_cannot_be_cleared(cls, v: bool | None) -> bool:
        if v is None:
            raise ValueError("flag cannot be cleared")
        return v

    @field_validator("email")
    @classmethod
    def email_cannot_be_cleared(cls, v: EmailStr | None) -> EmailStr:
        if v is None:
            raise ValueError("email cannot be cleared")
        return v


class UpdateCompanyUserRequest(UpdateCompanyUserInput):
    pass


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class PasswordResetInput(BaseModel):
    email: EmailStr


class PasswordResetRequest(PasswordResetInput):
    pass


class ResetPasswordInput(BaseModel):
    token: str
    new_password: str


class ResetPasswordRequest(ResetPasswordInput):
    pass
