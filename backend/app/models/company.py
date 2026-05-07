from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, Sequence

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.kp_event import KpEventBooking, KpEventRegistrationException
    from app.models.user import User


class Company(BaseEntity, table=True):
    name: str = Field(index=True, unique=True)

    users: Sequence["User"] = Relationship(back_populates="company")
    invites: Sequence["CompanyInvite"] = Relationship(back_populates="company")
    bookings: Sequence["KpEventBooking"] = Relationship(back_populates="company")
    kp_profile: "KpCompanyProfile" = Relationship(
        back_populates="company",
        sa_relationship_kwargs={"useSequence": False},
    )
    registration_exceptions: Sequence["KpEventRegistrationException"] = Relationship(
        back_populates="company"
    )


class KpCompanyProfile(BaseEntity, table=True):
    company_id: UUID = Field(foreign_key="company.id", unique=True)

    invoice_address: str = Field(default="")
    shipping_address: str = Field(default="")
    contact_email: EmailStr | None = Field(default=None)
    kp_contact_user_id: UUID | None = Field(default=None, foreign_key="user.id")

    company: Company = Relationship(back_populates="kp_profile")
    kp_contact_user: "User" = Relationship(back_populates="kp_company_profiles")


class CompanyInvite(BaseEntity, table=True):
    token: str = Field(index=True, unique=True)
    company_id: UUID = Field(foreign_key="company.id")
    invited_email: EmailStr
    is_used: bool = Field(default=False)
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    company: Company = Relationship(back_populates="invites")
