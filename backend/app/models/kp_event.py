from datetime import date
from enum import Enum
import re
from typing import Self
from uuid import UUID, uuid4

from pydantic import field_validator, model_validator
from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from app.models.company import Company
from app.models.user import User


class KpEvent(SQLModel, table=True):
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

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    registration_open: date
    registration_end: date
    finalization_deadline: date  # deadline for finalizing the booking. after this date, no changes to the booking are allowed.
    event_date: date

    booth_zones: list["KpEventBoothZone"] = Relationship(back_populates="event")
    bookings: list["KpEventBooking"] = Relationship(back_populates="event")
    services: list["KpEventService"] = Relationship(back_populates="event")

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
        if self.finalization_deadline < self.registration_end:
            raise ValueError("finalization_deadline must be after registration_end")
        if self.finalization_deadline >= self.event_date:
            raise ValueError("finalization_deadline must be before event_date")
        return self


class KpEventBooking(SQLModel, table=True):

    __table_args__ = (UniqueConstraint("event_id", "company_id", "booth_zone_id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="kpevent.id")
    company_id: UUID = Field(foreign_key="company.id")
    booth_zone_id: UUID = Field(foreign_key="kpeventboothzone.id")

    main_contact_id: UUID = Field(foreign_key="user.id")

    finalized: bool = Field(default=False)

    # TODO: Add booth_id reference

    deleted: bool = Field(default=False)

    event: KpEvent | None = Relationship(back_populates="bookings")
    company: Company | None = Relationship(back_populates="bookings")
    booth_zone: "KpEventBoothZone" = Relationship(back_populates="bookings")
    main_contact: User | None = Relationship(back_populates="main_contact_bookings")
    services: list["KpEventBookingService"] = Relationship(back_populates="booking")


class KpEventBoothZoneServiceLink(SQLModel, table=True):
    booth_zone_id: UUID = Field(foreign_key="kpeventboothzone.id", primary_key=True)
    service_id: UUID = Field(foreign_key="kpeventservice.id", primary_key=True)
    included_quantity: int = Field(default=1, ge=1)

    booth_zone: "KpEventBoothZone" = Relationship(back_populates="included_services")
    service: "KpEventService" = Relationship(back_populates="booth_zones")


class KpEventBoothZone(SQLModel, table=True):

    __table_args__ = (
        UniqueConstraint("event_id", "name"),
        UniqueConstraint("event_id", "color"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="kpevent.id")

    name: str = Field(min_length=1)
    description: str
    color: str = Field(default="#000000")
    order: int = Field(default=100, ge=0)

    booth_size: float = Field(default=0, ge=0)  # square meters
    base_price: int = Field(default=0, ge=0)  # cents

    deleted: bool = Field(default=False)

    event: KpEvent | None = Relationship(back_populates="booth_zones")
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


class KpEventServiceRequirement(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    service_id: UUID = Field(foreign_key="kpeventservice.id")
    type: KpEventServiceRequirementType
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=20)
    order: int = Field(default=100, ge=0)

    service: "KpEventService" = Relationship(back_populates="requirements")


class KpEventService(SQLModel, table=True):

    __table_args__ = (UniqueConstraint("event_id", "name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
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

    deleted: bool = Field(default=False)

    event: KpEvent | None = Relationship(back_populates="services")
    booth_zones: list["KpEventBoothZoneServiceLink"] = Relationship(
        back_populates="service"
    )
    booking_services: list["KpEventBookingService"] = Relationship(
        back_populates="service"
    )
    requirements: list[KpEventServiceRequirement] = Relationship(
        back_populates="service",
    )


class KpEventBookingService(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
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
