from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.kp_event import KpEventBooking, KpEventRegistrationException
    from app.models.user import User


class Company(BaseEntity, table=True):
    name: str = Field(index=True, unique=True)

    users: list["User"] = Relationship(back_populates="company")
    invites: list["CompanyInvite"] = Relationship(back_populates="company")
    bookings: list["KpEventBooking"] = Relationship(back_populates="company")
    registration_exceptions: list["KpEventRegistrationException"] = Relationship(
        back_populates="company"
    )


class CompanyInvite(BaseEntity, table=True):
    token: str = Field(index=True, unique=True)
    company_id: UUID = Field(foreign_key="company.id")
    invited_email: EmailStr
    is_used: bool = Field(default=False)
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    company: Company = Relationship(back_populates="invites")
