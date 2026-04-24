from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship

from app.core.utils import normalize_email
from app.models.base import BaseEntity, BaseLink, BaseToken
from app.models.company import Company

if TYPE_CHECKING:
    from app.models.kp_event import KpEventBooking


class UserRole(BaseLink, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    role_id: UUID = Field(foreign_key="role.id", primary_key=True)


class Role(BaseEntity, table=True):
    name: str = Field(index=True, unique=True)

    users: list["User"] = Relationship(back_populates="roles", link_model=UserRole)


class User(BaseEntity, table=True):
    email: EmailStr = Field(unique=True, index=True)
    sub: str | None = Field(default=None, index=True)
    password: str | None = None

    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    phone_number: str | None = None

    is_staff: bool = False
    is_admin: bool = False
    is_company: bool = False

    user_confirmed: bool = False
    email_confirmed: bool = False

    roles: List["Role"] = Relationship(back_populates="users", link_model=UserRole)

    company_id: UUID | None = Field(default=None, foreign_key="company.id", index=True)
    company: Optional["Company"] = Relationship(back_populates="users")
    main_contact_bookings: list["KpEventBooking"] = Relationship(
        back_populates="main_contact"
    )

    @field_validator("email", mode="after")
    @classmethod
    def transform_email(cls, v: str) -> str:
        return normalize_email(v)


class RefreshToken(BaseToken, table=True):
    pass


class ForgetPasswordToken(BaseToken, table=True):
    pass


class ConfirmEmailToken(BaseToken, table=True):
    pass
