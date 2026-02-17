from pydantic import BaseModel
from uuid import UUID


class CompanyResponse(BaseModel):
    id: UUID
    name: str


class UnconfirmedUserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    user_confirmed: bool
    email_confirmed: bool
    company: CompanyResponse | None = None


class RegisterUserRequest(BaseModel):
    email: str
    password: str
    company_id: str | None = None
    company_name: str | None = None


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
