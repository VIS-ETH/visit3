from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.utils import strip_text


class CompanyResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class CompanyResponse(CompanyResult):
    pass


class CompanyUserResult(BaseModel):
    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    user_confirmed: bool
    email_confirmed: bool
    company: CompanyResponse | None = None


class CompanyUserResponse(CompanyUserResult):
    pass


class UserResult(BaseModel):
    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    is_staff: bool
    is_admin: bool
    is_company: bool
    user_confirmed: bool
    email_confirmed: bool
    company_id: UUID | None = None
    company: CompanyResponse | None = None


class UserResponse(UserResult):
    pass


class RegisterUserInput(BaseModel):
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    phone_number: str | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str) -> str:
        return strip_text(v)


class RegisterUserRequest(RegisterUserInput):
    pass


class UpdateUserProfileInput(BaseModel):
    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    phone_number: str | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str | None) -> str | None:
        return strip_text(v)


class UpdateUserProfileRequest(UpdateUserProfileInput):
    pass


class UpdateCompanyUserInput(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    phone_number: str | None = None
    company_id: UUID | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str | None) -> str | None:
        return strip_text(v)


class UpdateCompanyUserRequest(UpdateCompanyUserInput):
    pass


class TokenResult(BaseModel):
    access_token: str
    token_type: str


class Token(TokenResult):
    pass


class TokenData(BaseModel):
    username: str | None = None


class ForgetPasswordInput(BaseModel):
    email: EmailStr


class ForgetPasswordRequest(ForgetPasswordInput):
    pass


class ResetPasswordInput(BaseModel):
    token: str
    new_password: str


class ResetPasswordRequest(ResetPasswordInput):
    pass
