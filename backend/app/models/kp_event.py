from datetime import date
from enum import Enum
import re
from typing import Self
from uuid import UUID

from pydantic import field_validator, model_validator
from sqlalchemy import CheckConstraint, Column, Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, Relationship, UniqueConstraint

from app.core.utils import strip_text
from app.models.base import BaseEntity, BaseLink
from app.models.company import Company
from app.models.user import User


class KpEvent(BaseEntity, table=True):
    __table_args__ = (
        CheckConstraint(
            "registration_open < registration_end",
            name="kpevent_registration_open_before_end",
        ),
        CheckConstraint(
            "registration_end < event_date",
            name="kpevent_registration_end_before_event_date",
        ),
        CheckConstraint(
            "finalization_deadline >= registration_end",
            name="kpevent_finalization_on_or_after_registration_end",
        ),
        CheckConstraint(
            "finalization_deadline < event_date",
            name="kpevent_finalization_before_event_date",
        ),
    )

    name: str = Field(index=True, unique=True)
    registration_open: date
    registration_end: date
    finalization_deadline: date  # deadline for finalizing the booking. after this date, no changes to the booking are allowed.
    nametags_deadline: date  # deadline for submitting nametags. after this date, no nametags can be changed.
    event_date: date

    booth_zones: list["KpEventBoothZone"] = Relationship(back_populates="event")
    bookings: list["KpEventBooking"] = Relationship(back_populates="event")
    services: list["KpEventService"] = Relationship(back_populates="event")
    registration_exceptions: list["KpEventRegistrationException"] = Relationship(
        back_populates="event"
    )

    def is_registration_open(self) -> bool:
        today = date.today()
        return self.registration_open <= today <= self.registration_end

    def is_finalization_deadline_passed(self) -> bool:
        today = date.today()
        return self.finalization_deadline < today

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.registration_open >= self.registration_end:
            raise ValueError("registration_end must be after registration_open")
        if self.registration_end >= self.event_date:
            raise ValueError("event_date must be after registration_end")
        if self.nametags_deadline < self.registration_end:
            raise ValueError("nametags_deadline must be after registration_end")
        if self.nametags_deadline >= self.event_date:
            raise ValueError("nametags_deadline must be before event_date")
        if self.finalization_deadline < self.registration_end:
            raise ValueError("finalization_deadline must be after registration_end")
        if self.finalization_deadline >= self.event_date:
            raise ValueError("finalization_deadline must be before event_date")
        return self


class KpEventBooking(BaseEntity, table=True):
    __table_args__ = (
        UniqueConstraint("event_id", "company_id", "booth_zone_id"),
        UniqueConstraint(
            "event_id", "booth_zone_id", "booth_nr"
        ),  # each booking within a zone must have a unique booth number
    )

    event_id: UUID = Field(foreign_key="kpevent.id")
    company_id: UUID = Field(foreign_key="company.id")
    booth_zone_id: UUID = Field(foreign_key="kpeventboothzone.id")

    main_contact_id: UUID = Field(foreign_key="user.id")

    finalized: bool = Field(default=False)

    booth_nr: int = Field(ge=1)  # booth number within the booth zone

    event: "KpEvent" = Relationship(back_populates="bookings")
    company: Company = Relationship(back_populates="bookings")
    booth_zone: "KpEventBoothZone" = Relationship(back_populates="bookings")
    main_contact: User = Relationship(back_populates="main_contact_bookings")
    services: list["KpEventBookingService"] = Relationship(back_populates="booking")
    name_tags: list["NameTag"] = Relationship(back_populates="booking")
    company_details: "KpBookingCompanyDetails" = Relationship(
        back_populates="booking",
        sa_relationship_kwargs={"uselist": False},
    )


class NameTag(BaseEntity, table=True):
    booking_id: UUID = Field(foreign_key="kpeventbooking.id")

    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    position: str = Field(min_length=1)

    booking: "KpEventBooking" = Relationship(back_populates="name_tags")

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, value: str) -> str:
        return strip_text(value)


class KpEventBoothZoneServiceLink(BaseLink, table=True):
    booth_zone_id: UUID = Field(foreign_key="kpeventboothzone.id", primary_key=True)
    service_id: UUID = Field(foreign_key="kpeventservice.id", primary_key=True)
    included_quantity: int = Field(default=1, ge=1)

    booth_zone: "KpEventBoothZone" = Relationship(back_populates="included_services")
    service: "KpEventService" = Relationship(back_populates="booth_zones")


class KpEventBoothZone(BaseEntity, table=True):
    __table_args__ = (
        UniqueConstraint("event_id", "name"),
        UniqueConstraint("event_id", "color"),
    )

    event_id: UUID = Field(foreign_key="kpevent.id")

    name: str = Field(min_length=1)
    description: str
    color: str = Field(default="#000000")
    order: int = Field(default=100, ge=0)
    capacity: int = Field(default=0, ge=0)

    booth_size: float = Field(default=0, ge=0)  # square meters
    base_price: int = Field(default=0, ge=0)  # cents

    event: "KpEvent" = Relationship(back_populates="booth_zones")
    included_services: list["KpEventBoothZoneServiceLink"] = Relationship(
        back_populates="booth_zone"
    )
    bookings: list["KpEventBooking"] = Relationship(back_populates="booth_zone")

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not re.fullmatch(r"^#[0-9A-Fa-f]{6}$", value):
            raise ValueError("color must be a valid hex color in #RRGGBB format")
        return value


class KpEventServiceRequirementType(Enum):
    # TODO: Perhaps we should have a more flexible the types, mime-type?
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    PDF = "pdf"
    VIDEO = "video"


class KpEventServiceRequirement(BaseEntity, table=True):
    service_id: UUID = Field(foreign_key="kpeventservice.id")
    type: KpEventServiceRequirementType
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=20)
    order: int = Field(default=100, ge=0)

    service: "KpEventService" = Relationship(back_populates="requirements")


class KpEventService(BaseEntity, table=True):
    __table_args__ = (UniqueConstraint("event_id", "name"),)

    event_id: UUID = Field(foreign_key="kpevent.id")

    name: str = Field(min_length=1)
    description: str
    image_url: str | None = None
    # description of the service that will be shown to the company after they have booked the service.
    # e.g. "Please send us the parcels to the following address: ..."
    confirmation_description: str | None = None
    order: int = Field(default=100, ge=0)

    price: int = Field(default=0, ge=0)  # cents
    # how many of this service can be ordered by a single booking. 0 means unlimited.
    max_quantity_per_booking: int = Field(default=1, ge=1)
    # how many of this service can be ordered in total by all bookings. 0 means unlimited.
    max_total_quantity: int = Field(default=0, ge=0)

    # if false, service is no longer available for booking. already booked services are not affected.
    is_active: bool = Field(default=True)

    event: "KpEvent" = Relationship(back_populates="services")
    booth_zones: list["KpEventBoothZoneServiceLink"] = Relationship(
        back_populates="service"
    )
    booking_services: list["KpEventBookingService"] = Relationship(
        back_populates="service"
    )
    requirements: list["KpEventServiceRequirement"] = Relationship(
        back_populates="service",
    )


class KpEventBookingService(BaseEntity, table=True):
    booking_id: UUID = Field(foreign_key="kpeventbooking.id")
    service_id: UUID = Field(foreign_key="kpeventservice.id")

    quantity: int = Field(default=1, ge=1)

    included_quantity: int = Field(
        default=0, ge=0
    )  # quantity of the service that is already included in the booking.

    booking: "KpEventBooking" = Relationship(back_populates="services")
    service: "KpEventService" = Relationship(back_populates="booking_services")

    @property
    def charged_quantity(self) -> int:
        """
        The charged quantity of the service. Subtracts the quantity that is already included in the booking (e.g. through the selected booth zone).
        """
        return max(self.quantity - self.included_quantity, 0)


class KpCompanyLanguage(str, Enum):
    ENGLISH = "ENGLISH"
    GERMAN = "GERMAN"
    FRENCH = "FRENCH"
    ITALIAN = "ITALIAN"


_kp_company_language_pg_enum = SAEnum(
    KpCompanyLanguage,
    name="kpcompanylanguage",
    native_enum=True,
)


class KpIndustry(BaseEntity, table=True):
    name: str = Field(min_length=1, index=True, unique=True)

    company_details_links: list["KpBookingCompanyDetailsIndustryLink"] = Relationship(
        back_populates="industry",
    )


class KpBookingCompanyDetails(BaseEntity, table=True):
    booking_id: UUID = Field(foreign_key="kpeventbooking.id", unique=True)

    profile: str = Field(default="")  # markdown
    brand_name: str = Field(default="")
    address: str = Field(default="")
    contact_person: str = Field(default="")
    places_of_work: str = Field(default="")

    employees_count: int | None = Field(default=None, ge=0)
    employees_count_switzerland: int | None = Field(default=None, ge=0)

    offer_internship: bool = Field(default=False)
    offer_part_time: bool = Field(default=False)
    offer_thesis: bool = Field(default=False)

    languages: list[KpCompanyLanguage] = Field(
        default_factory=list,
        sa_column=Column(
            ARRAY(_kp_company_language_pg_enum),
            nullable=False,
        ),
    )

    booking: "KpEventBooking" = Relationship(back_populates="company_details")
    industry_links: list["KpBookingCompanyDetailsIndustryLink"] = Relationship(
        back_populates="booking_company_details",
    )


class KpBookingCompanyDetailsIndustryLink(BaseLink, table=True):
    booking_company_details_id: UUID = Field(
        foreign_key="kpbookingcompanydetails.id",
        primary_key=True,
    )
    industry_id: UUID = Field(foreign_key="kpindustry.id", primary_key=True)

    booking_company_details: "KpBookingCompanyDetails" = Relationship(
        back_populates="industry_links",
    )
    industry: "KpIndustry" = Relationship(back_populates="company_details_links")


class KpEventRegistrationException(BaseEntity, table=True):
    """Allows specific companies to register after the event's registration deadline."""

    __table_args__ = (UniqueConstraint("event_id", "company_id"),)

    event_id: UUID = Field(foreign_key="kpevent.id")
    company_id: UUID = Field(foreign_key="company.id")
    allowed_until: date

    event: "KpEvent" = Relationship(back_populates="registration_exceptions")
    company: "Company" = Relationship(back_populates="registration_exceptions")
