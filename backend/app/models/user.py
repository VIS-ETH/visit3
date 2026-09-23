from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship

from app.core.config import get_settings
from app.core.utils import normalize_email, strip_text
from app.models.base import (
    TIMESTAMPTZ,
    BaseEntity,
    BaseLink,
    BaseToken,
    unique_among_active_index,
)
from app.models.company import Company

if TYPE_CHECKING:
    from app.models.company import KpCompanyProfile


class UserRole(BaseLink, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    role_id: UUID = Field(foreign_key="role.id", primary_key=True)


class Role(BaseEntity, table=True):
    name: str = Field(index=True, unique=True)

    users: list["User"] = Relationship(back_populates="roles", link_model=UserRole)


class User(BaseEntity, table=True):
    __table_args__ = (unique_among_active_index("ix_user_email", "email"),)

    email: EmailStr
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

    pending_invite_token: str | None = Field(default=None)

    roles: list["Role"] = Relationship(
        back_populates="users",
        link_model=UserRole,
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    company_id: UUID | None = Field(default=None, foreign_key="company.id", index=True)
    company: Company = Relationship(
        back_populates="users", sa_relationship_kwargs={"lazy": "noload"}
    )
    kp_company_profiles: list["KpCompanyProfile"] = Relationship(
        back_populates="kp_contact_user"
    )

    @property
    def display_name(self) -> str:
        parts = [part for part in (self.first_name, self.last_name) if part]
        return " ".join(parts) if parts else self.email

    @property
    def is_kp_president(self) -> bool:
        if self.is_admin:
            return True
        president_role = get_settings().VISIT_KP_PRESIDENT_ROLE
        return any(role.name == president_role for role in self.roles)

    @field_validator("email", mode="after")
    @classmethod
    def transform_email(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: str | None) -> str | None:
        return strip_text(v)


class RefreshToken(BaseToken, table=True):
    rotated_at: datetime | None = Field(
        default=None,
        nullable=True,
        sa_type=TIMESTAMPTZ,
    )


class ResetPasswordToken(BaseToken, table=True):
    pass


class ConfirmEmailToken(BaseToken, table=True):
    pass
