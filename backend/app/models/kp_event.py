import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Self
from uuid import UUID

from pydantic import EmailStr, field_validator, model_validator
from sqlalchemy import CheckConstraint, Column, Integer
from sqlalchemy import Sequence as SQLSequence
from sqlmodel import (
    Field,
    Relationship,
    UniqueConstraint,
)

from app.core.utils import strip_text
from app.models.base import (
    NOT_DELETED,
    PERMILLE_PER_PERCENT,
    TIMESTAMPTZ,
    BaseEntity,
    BaseLink,
    Cents,
    Permille,
    SquareMeters,
    unique_among_active_index,
    unique_partial_index,
)
from app.models.company import (
    PROFILE_DESCRIPTION_MAX_LENGTH,
    Company,
    KpCompanyLanguage,
    company_language_column,
    normalize_country_code,
)
from app.models.industry import Industry
from app.models.storage import StoredFile

ACTIVE_BOOKING = f"status NOT IN ('CANCELLED', 'REJECTED') AND {NOT_DELETED}"
UNLIMITED_TOTAL_QUANTITY = 0
MAX_SERVICE_QUANTITY = 999
DEFAULT_MAX_NAMETAGS_PER_BOOKING = 10
LAYOUT_DESCRIPTION_MAX_LENGTH = 2000


class KpServiceCategory(str, Enum):
    SERVICE = "SERVICE"
    BOOTH_ELEMENT = "BOOTH_ELEMENT"


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
        CheckConstraint(
            "nametags_deadline >= registration_end",
            name="kpevent_nametags_on_or_after_registration_end",
        ),
        CheckConstraint(
            "nametags_deadline < event_date",
            name="kpevent_nametags_before_event_date",
        ),
    )

    name: str = Field(index=True, unique=True)
    registration_open: date
    registration_end: date
    finalization_deadline: date
    nametags_deadline: date
    event_date: date

    vat_rate_permille: Permille = Field(default=81, ge=0, le=1000)
    terms_url: str | None = Field(default=None)
    notification_email: EmailStr | None = Field(default=None)
    finalization_reminder_days: int = Field(default=3, ge=0)
    max_nametags_per_booking: int = Field(
        default=DEFAULT_MAX_NAMETAGS_PER_BOOKING, ge=1, le=MAX_SERVICE_QUANTITY
    )

    booth_zones: list["KpEventBoothZone"] = Relationship(back_populates="event")
    bookings: list["KpEventBooking"] = Relationship(back_populates="event")
    services: list["KpEventService"] = Relationship(back_populates="event")
    registration_exceptions: list["KpEventRegistrationException"] = Relationship(
        back_populates="event"
    )
    nametag_background: "KpEventNametagBackground" = Relationship(
        back_populates="event",
        sa_relationship_kwargs={"uselist": False},
    )

    @property
    def vat_rate_percent(self) -> Decimal:
        return Decimal(self.vat_rate_permille) / PERMILLE_PER_PERCENT

    def is_registration_open(self) -> bool:
        today = date.today()
        return self.registration_open <= today <= self.registration_end

    def is_finalization_deadline_passed(self) -> bool:
        today = date.today()
        return self.finalization_deadline < today

    def is_nametags_deadline_passed(self) -> bool:
        return self.nametags_deadline < date.today()

    @property
    def finalization_reminder_date(self) -> date:
        return self.finalization_deadline - timedelta(
            days=self.finalization_reminder_days
        )

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


class KpBookingStatus(str, Enum):
    REGISTERED = "REGISTERED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


INACTIVE_BOOKING_STATUSES = (KpBookingStatus.CANCELLED, KpBookingStatus.REJECTED)


class KpEventBooking(BaseEntity, table=True):
    __table_args__ = (
        unique_partial_index(
            "ix_kpeventbooking_event_id_company_id_booth_zone_id",
            "event_id",
            "company_id",
            "booth_zone_id",
            where=ACTIVE_BOOKING,
        ),
        unique_partial_index(
            "ix_kpeventbooking_event_id_booth_zone_id_booth_nr",
            "event_id",
            "booth_zone_id",
            "booth_nr",
            where=f"booth_nr IS NOT NULL AND {ACTIVE_BOOKING}",
        ),
    )

    event_id: UUID = Field(foreign_key="kpevent.id")
    company_id: UUID = Field(foreign_key="company.id")
    booth_zone_id: UUID = Field(foreign_key="kpeventboothzone.id")

    status: KpBookingStatus = Field(default=KpBookingStatus.REGISTERED)
    status_changed_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )
    status_note: str | None = Field(default=None)
    rejection_reason: str | None = Field(default=None)
    confirmed_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )
    reminder_sent_at: datetime | None = Field(
        default=None, nullable=True, sa_type=TIMESTAMPTZ
    )

    booking_number: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            SQLSequence("kpeventbooking_booking_number_seq", start=1000),
            nullable=False,
            unique=True,
        ),
    )

    booth_nr: int | None = Field(default=None, ge=1)

    event: "KpEvent" = Relationship(back_populates="bookings")
    company: Company = Relationship(back_populates="bookings")
    booth_zone: "KpEventBoothZone" = Relationship(back_populates="bookings")
    services: list["KpEventBookingService"] = Relationship(back_populates="booking")
    name_tags: list["NameTag"] = Relationship(back_populates="booking")
    upgrade_waitlist_entries: list["KpEventBookingUpgradeWaitlist"] = Relationship(
        back_populates="booking"
    )
    company_details: Optional["KpBookingCompanyDetails"] = Relationship(
        back_populates="booking",
        sa_relationship_kwargs={"uselist": False},
    )

    @property
    def is_active(self) -> bool:
        return self.status not in INACTIVE_BOOKING_STATUSES

    @property
    def total_price(self) -> int:
        return self.booth_zone.base_price + sum(
            booking_service.charged_quantity * booking_service.service.price
            for booking_service in self.services
        )

    @property
    def booked_services_count(self) -> int:
        return len(self.services)

    @property
    def booked_services_summary(self) -> str:
        return "; ".join(
            f"{booking_service.service.name} x{booking_service.quantity}"
            for booking_service in self.services
        )

    @property
    def nametag_count(self) -> int:
        return len(self.name_tags)

    @property
    def waitlist_count(self) -> int:
        return len(self.upgrade_waitlist_entries)

    @property
    def company_details_submitted(self) -> bool:
        return self.company_details is not None


class KpEventBookingUpgradeWaitlist(BaseEntity, table=True):
    __table_args__ = (UniqueConstraint("booking_id", "target_booth_zone_id"),)

    booking_id: UUID = Field(foreign_key="kpeventbooking.id")
    target_booth_zone_id: UUID = Field(foreign_key="kpeventboothzone.id")

    priority_rank: int | None = Field(default=None, ge=1)

    booking: "KpEventBooking" = Relationship(back_populates="upgrade_waitlist_entries")
    target_booth_zone: "KpEventBoothZone" = Relationship(
        back_populates="upgrade_waitlist_entries"
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
    included_quantity: int = Field(default=1, ge=1, le=MAX_SERVICE_QUANTITY)

    booth_zone: "KpEventBoothZone" = Relationship(back_populates="included_services")
    service: "KpEventService" = Relationship(back_populates="booth_zones")


class KpEventBoothZone(BaseEntity, table=True):
    __table_args__ = (
        unique_among_active_index(
            "ix_kpeventboothzone_event_id_name", "event_id", "name"
        ),
        unique_among_active_index(
            "ix_kpeventboothzone_event_id_color", "event_id", "color"
        ),
    )

    event_id: UUID = Field(foreign_key="kpevent.id")

    name: str = Field(min_length=1)
    description: str
    color: str = Field(default="#000000")
    order: int = Field(default=100, ge=0)
    capacity: int = Field(default=0, ge=0)

    booth_size: SquareMeters = Field(default=0, ge=0)
    base_price: Cents = Field(default=0, ge=0)

    layout_description: str | None = Field(
        default=None, max_length=LAYOUT_DESCRIPTION_MAX_LENGTH
    )
    layout_stored_file_id: UUID | None = Field(
        default=None, foreign_key="storedfile.id", unique=True
    )

    event: "KpEvent" = Relationship(back_populates="booth_zones")
    layout_stored_file: StoredFile | None = Relationship()
    included_services: list["KpEventBoothZoneServiceLink"] = Relationship(
        back_populates="booth_zone"
    )
    bookings: list["KpEventBooking"] = Relationship(back_populates="booth_zone")
    upgrade_waitlist_entries: list["KpEventBookingUpgradeWaitlist"] = Relationship(
        back_populates="target_booth_zone"
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not re.fullmatch(r"^#[0-9A-Fa-f]{6}$", value):
            raise ValueError("color must be a valid hex color in #RRGGBB format")
        return value


class KpEventServiceRequirementType(Enum):
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
    __table_args__ = (
        unique_among_active_index(
            "ix_kpeventservice_event_id_name", "event_id", "name"
        ),
    )

    event_id: UUID = Field(foreign_key="kpevent.id")

    name: str = Field(min_length=1)
    description: str
    category: KpServiceCategory = Field(default=KpServiceCategory.SERVICE)
    unit_label: str | None = Field(default=None)
    image_stored_file_id: UUID | None = Field(
        default=None, foreign_key="storedfile.id", unique=True
    )
    confirmation_description: str | None = None
    order: int = Field(default=100, ge=0)

    price: Cents = Field(default=0, ge=0)
    max_quantity_per_booking: int = Field(default=1, ge=1, le=MAX_SERVICE_QUANTITY)
    max_total_quantity: int = Field(default=UNLIMITED_TOTAL_QUANTITY, ge=0)

    is_active: bool = Field(default=True)

    event: "KpEvent" = Relationship(back_populates="services")
    image_stored_file: StoredFile | None = Relationship()
    booth_zones: list["KpEventBoothZoneServiceLink"] = Relationship(
        back_populates="service"
    )
    booking_services: list["KpEventBookingService"] = Relationship(
        back_populates="service"
    )
    requirements: list["KpEventServiceRequirement"] = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"order_by": "KpEventServiceRequirement.order"},
    )


class KpEventBookingService(BaseEntity, table=True):
    booking_id: UUID = Field(foreign_key="kpeventbooking.id")
    service_id: UUID = Field(foreign_key="kpeventservice.id")

    quantity: int = Field(default=1, ge=1, le=MAX_SERVICE_QUANTITY)

    included_quantity: int = Field(default=0, ge=0, le=MAX_SERVICE_QUANTITY)

    booking: "KpEventBooking" = Relationship(back_populates="services")
    service: "KpEventService" = Relationship(back_populates="booking_services")
    requirement_file_links: list["KpEventBookingServiceFileLink"] = Relationship(
        back_populates="booking_service"
    )

    @property
    def charged_quantity(self) -> int:
        return max(self.quantity - self.included_quantity, 0)


class KpEventBookingServiceFileLink(BaseEntity, table=True):
    __table_args__ = (
        UniqueConstraint("booking_service_id", "requirement_id"),
        CheckConstraint(
            "(stored_file_id IS NULL) <> (text_value IS NULL)",
            name="kpeventbookingservicefilelink_exactly_one_answer",
        ),
    )

    booking_service_id: UUID = Field(foreign_key="kpeventbookingservice.id")
    requirement_id: UUID = Field(foreign_key="kpeventservicerequirement.id")
    stored_file_id: UUID | None = Field(
        default=None, foreign_key="storedfile.id", unique=True
    )
    text_value: str | None = Field(default=None)

    booking_service: "KpEventBookingService" = Relationship(
        back_populates="requirement_file_links"
    )
    requirement: "KpEventServiceRequirement" = Relationship()
    stored_file: StoredFile | None = Relationship()


class KpEventNametagBackground(BaseEntity, table=True):
    __table_args__ = (
        unique_among_active_index("ix_kpeventnametagbackground_event_id", "event_id"),
    )

    event_id: UUID = Field(foreign_key="kpevent.id")
    stored_file_id: UUID = Field(foreign_key="storedfile.id", unique=True)

    event: KpEvent = Relationship(back_populates="nametag_background")
    stored_file: StoredFile = Relationship()


class KpBookingCompanyDetails(BaseEntity, table=True):
    booking_id: UUID = Field(foreign_key="kpeventbooking.id", unique=True)
    confirmed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=TIMESTAMPTZ,
    )

    description: str = Field(default="", max_length=PROFILE_DESCRIPTION_MAX_LENGTH)
    website: str | None = Field(default=None)

    brand_name: str = Field(default="")
    contact_person: str = Field(default="")
    contact_email: EmailStr | None = Field(default=None)
    contact_phone: str | None = Field(default=None)
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

    booking: "KpEventBooking" = Relationship(back_populates="company_details")
    industry_links: list["KpBookingCompanyDetailsIndustryLink"] = Relationship(
        back_populates="booking_company_details",
    )

    @field_validator("billing_country")
    @classmethod
    def validate_billing_country(cls, value: str) -> str:
        return normalize_country_code(value)

    @property
    def industry_names(self) -> list[str]:
        return [link.industry_name for link in self.industry_links]


class KpBookingCompanyDetailsIndustryLink(BaseLink, table=True):
    booking_company_details_id: UUID = Field(
        foreign_key="kpbookingcompanydetails.id",
        primary_key=True,
    )
    industry_id: UUID = Field(foreign_key="industry.id", primary_key=True)
    industry_name: str = Field(default="")

    booking_company_details: "KpBookingCompanyDetails" = Relationship(
        back_populates="industry_links",
    )
    industry: Industry = Relationship(back_populates="snapshot_links")


class KpEventRegistrationException(BaseEntity, table=True):
    __table_args__ = (UniqueConstraint("event_id", "company_id"),)

    event_id: UUID = Field(foreign_key="kpevent.id")
    company_id: UUID = Field(foreign_key="company.id")
    allowed_until: date

    event: "KpEvent" = Relationship(back_populates="registration_exceptions")
    company: "Company" = Relationship(back_populates="registration_exceptions")
