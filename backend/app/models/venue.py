from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from app.models.base import BaseEntity, unique_among_active_index
from app.models.kp_event import KpEventBoothZone
from app.models.storage import StoredFile

DEFAULT_VENUE_LAYOUT_WIDTH = 1000
DEFAULT_VENUE_LAYOUT_HEIGHT = 700


class KpVenueLayout(BaseEntity, table=True):
    __table_args__ = (
        unique_among_active_index("ix_kpvenuelayout_event_id_name", "event_id", "name"),
    )

    event_id: UUID = Field(foreign_key="kpevent.id")

    name: str = Field(min_length=1)
    order: int = Field(default=100, ge=0)
    background_stored_file_id: UUID | None = Field(
        default=None, foreign_key="storedfile.id", unique=True
    )
    width: int = Field(default=DEFAULT_VENUE_LAYOUT_WIDTH, ge=1)
    height: int = Field(default=DEFAULT_VENUE_LAYOUT_HEIGHT, ge=1)
    is_active: bool = Field(default=True)

    background_stored_file: StoredFile | None = Relationship()
    zone_shapes: list["KpVenueZoneShape"] = Relationship(back_populates="layout")
    booths: list["KpVenueBooth"] = Relationship(back_populates="layout")


class KpVenueZoneShape(BaseEntity, table=True):
    layout_id: UUID = Field(foreign_key="kpvenuelayout.id")
    booth_zone_id: UUID = Field(foreign_key="kpeventboothzone.id")

    shape: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    label_position: list[float] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )

    layout: KpVenueLayout = Relationship(back_populates="zone_shapes")
    booth_zone: KpEventBoothZone = Relationship()


class KpVenueBooth(BaseEntity, table=True):
    __table_args__ = (
        unique_among_active_index(
            "ix_kpvenuebooth_layout_id_booth_nr", "layout_id", "booth_nr"
        ),
    )

    layout_id: UUID = Field(foreign_key="kpvenuelayout.id")
    booth_zone_id: UUID = Field(foreign_key="kpeventboothzone.id")

    booth_nr: int = Field(ge=1)
    x: float
    y: float
    rotation: float | None = Field(default=None)

    layout: KpVenueLayout = Relationship(back_populates="booths")
    booth_zone: KpEventBoothZone = Relationship()
