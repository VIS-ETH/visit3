import re
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from pydantic import EmailStr, field_validator
from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, Relationship

from app.models.base import TIMESTAMPTZ, BaseEntity, unique_among_active_index
from app.models.storage import StoredFile

if TYPE_CHECKING:
    from app.models.industry import KpCompanyProfileIndustryLink
    from app.models.kp_event import KpEventBooking, KpEventRegistrationException
    from app.models.user import User

PROFILE_DESCRIPTION_MAX_LENGTH = 2500

MANDATORY_PROFILE_FIELDS = (
    "description",
    "kp_contact_user_id",
    "billing_company_name",
    "billing_street",
    "billing_postal_code",
    "billing_city",
    "billing_country",
    "billing_email",
)

BOOKING_DEFERRED_PROFILE_FIELDS = ("description",)

BOOKING_REQUIRED_PROFILE_FIELDS = tuple(
    name
    for name in MANDATORY_PROFILE_FIELDS
    if name not in BOOKING_DEFERRED_PROFILE_FIELDS
)

COUNTRY_CODE_PATTERN = re.compile(r"[A-Z]{2}")


class KpCompanyLanguage(str, Enum):
    ENGLISH = "ENGLISH"
    GERMAN = "GERMAN"
    FRENCH = "FRENCH"
    ITALIAN = "ITALIAN"


def company_language_column() -> Column[Any]:
    language_enum = SAEnum(
        KpCompanyLanguage, name="kpcompanylanguage", native_enum=True
    )
    return Column(ARRAY(language_enum), nullable=False)


def normalize_country_code(value: str) -> str:
    normalized = value.strip().upper()
    if normalized and not COUNTRY_CODE_PATTERN.fullmatch(normalized):
        raise ValueError("country must be an ISO 3166-1 alpha-2 code")
    return normalized


class Company(BaseEntity, table=True):
    __table_args__ = (unique_among_active_index("ix_company_name", "name"),)

    name: str

    users: list["User"] = Relationship(back_populates="company")
    invites: list["CompanyInvite"] = Relationship(back_populates="company")
    bookings: list["KpEventBooking"] = Relationship(back_populates="company")
    kp_profile: "KpCompanyProfile" = Relationship(
        back_populates="company",
        sa_relationship_kwargs={"uselist": False},
    )
    registration_exceptions: list["KpEventRegistrationException"] = Relationship(
        back_populates="company"
    )


class KpCompanyProfile(BaseEntity, table=True):
    company_id: UUID = Field(foreign_key="company.id", unique=True)

    description: str = Field(default="", max_length=PROFILE_DESCRIPTION_MAX_LENGTH)
    website: str | None = Field(default=None)
    logo_stored_file_id: UUID | None = Field(
        default=None, foreign_key="storedfile.id", unique=True
    )

    brand_name: str = Field(default="")
    general_email: EmailStr | None = Field(default=None)
    general_phone: str | None = Field(default=None)
    places_of_work: str = Field(default="")

    employee_count_switzerland: int | None = Field(default=None, ge=0)
    employee_count_worldwide: int | None = Field(default=None, ge=0)

    offers_internships: bool = Field(default=False)
    offers_part_time: bool = Field(default=False)
    offers_theses: bool = Field(default=False)
    offers_graduate_positions: bool = Field(default=False)

    languages: list[KpCompanyLanguage] = Field(
        default_factory=list,
        sa_column=company_language_column(),
    )

    billing_company_name: str = Field(default="")
    billing_street: str = Field(default="")
    billing_house_number: str = Field(default="")
    billing_postal_code: str = Field(default="")
    billing_city: str = Field(default="")
    billing_country: str = Field(default="", max_length=2)
    billing_vat_number: str | None = Field(default=None)
    billing_email: EmailStr | None = Field(default=None)

    kp_contact_user_id: UUID | None = Field(default=None, foreign_key="user.id")
    profile_completed_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )

    company: Company = Relationship(back_populates="kp_profile")
    kp_contact_user: Optional["User"] = Relationship(
        back_populates="kp_company_profiles"
    )
    logo_stored_file: StoredFile | None = Relationship()
    industry_links: list["KpCompanyProfileIndustryLink"] = Relationship(
        back_populates="profile"
    )

    @field_validator("billing_country")
    @classmethod
    def validate_billing_country(cls, value: str) -> str:
        return normalize_country_code(value)

    def missing_profile_fields(self) -> list[str]:
        return [
            name
            for name in MANDATORY_PROFILE_FIELDS
            if not str(getattr(self, name) or "").strip()
        ]

    def missing_booking_profile_fields(self) -> list[str]:
        return [
            name
            for name in self.missing_profile_fields()
            if name in BOOKING_REQUIRED_PROFILE_FIELDS
        ]

    @property
    def is_complete(self) -> bool:
        return not self.missing_profile_fields()


class CompanyInvite(BaseEntity, table=True):
    token: str = Field(index=True, unique=True)
    company_id: UUID = Field(foreign_key="company.id")
    invited_email: EmailStr
    is_used: bool = Field(default=False)
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    company: Company = Relationship(back_populates="invites")
