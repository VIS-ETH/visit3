from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, func

from app.core.utils import normalize_email
from app.models.company import Company


class UserRole(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    role_id: UUID = Field(foreign_key="role.id", primary_key=True)


class Role(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)

    users: list["User"] = Relationship(back_populates="roles", link_model=UserRole)


class User(SQLModel, table=True):
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
    )
    email: str = Field(unique=True, index=True)
    sub: Optional[str] = Field(default=None, index=True)
    password: Optional[str]

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None

    is_staff: bool = False
    is_admin: bool = False
    is_company: bool = False

    user_confirmed: bool = False
    email_confirmed: bool = False

    roles: List["Role"] = Relationship(back_populates="users", link_model=UserRole)

    company_id: Optional[UUID] = Field(
        default=None, foreign_key="company.id", index=True
    )
    company: Optional["Company"] = Relationship(back_populates="users")

    @field_validator("email", mode="before")
    @classmethod
    def transform_email(cls, v: str) -> str:
        return normalize_email(v)


class RefreshToken(SQLModel, table=True):
    id: UUID = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False
    )
    user_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    token: str = Field(index=True, unique=True)

    is_revoked: bool = Field(default=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )


class ForgetPasswordToken(SQLModel, table=True):
    id: UUID = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False
    )
    user_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    token: str = Field(index=True, unique=True)

    is_revoked: bool = Field(default=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )


class ConfirmEmailToken(SQLModel, table=True):
    id: UUID = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False
    )
    user_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    token: str = Field(index=True, unique=True)

    is_revoked: bool = Field(default=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
