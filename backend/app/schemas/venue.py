from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.venue import (
    DEFAULT_VENUE_LAYOUT_HEIGHT,
    DEFAULT_VENUE_LAYOUT_WIDTH,
    KpVenueFloorPlan,
)
from app.schemas.kp import BoothZoneWithAvailabilityResult, StoredFileResponse

VenuePoint = tuple[float, float]

MIN_POLYGON_POINTS = 3
MAX_POLYGON_POINTS = 200
MAX_LAYOUT_ELEMENTS = 500


class VenuePolygonShape(BaseModel):
    type: Literal["polygon"]
    points: list[VenuePoint] = Field(
        min_length=MIN_POLYGON_POINTS, max_length=MAX_POLYGON_POINTS
    )


class VenueRectShape(BaseModel):
    type: Literal["rect"]
    x: float
    y: float
    w: float = Field(gt=0)
    h: float = Field(gt=0)


VenueShape = Annotated[VenuePolygonShape | VenueRectShape, Field(discriminator="type")]


def shape_extent_points(shape: VenuePolygonShape | VenueRectShape) -> list[VenuePoint]:
    if isinstance(shape, VenueRectShape):
        return [(shape.x, shape.y), (shape.x + shape.w, shape.y + shape.h)]
    return shape.points


class CreateVenueLayoutInput(BaseModel):
    name: str = Field(min_length=1)
    order: int = Field(default=100, ge=0)
    width: int = Field(default=DEFAULT_VENUE_LAYOUT_WIDTH, ge=1)
    height: int = Field(default=DEFAULT_VENUE_LAYOUT_HEIGHT, ge=1)
    is_active: bool = True
    floor_plan: KpVenueFloorPlan | None = None


class CreateVenueLayoutRequest(CreateVenueLayoutInput):
    pass


class UpdateVenueLayoutInput(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    order: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    floor_plan: KpVenueFloorPlan | None = None


class UpdateVenueLayoutRequest(UpdateVenueLayoutInput):
    pass


class VenueZoneShapeInput(BaseModel):
    booth_zone_id: UUID
    shape: VenueShape
    label_position: VenuePoint | None = None


class ReplaceVenueZoneShapesRequest(BaseModel):
    shapes: list[VenueZoneShapeInput] = Field(
        default_factory=lambda: [], max_length=MAX_LAYOUT_ELEMENTS
    )


class VenueBoothInput(BaseModel):
    booth_zone_id: UUID
    booth_nr: int = Field(ge=1)
    x: float
    y: float
    rotation: float | None = None


class ReplaceVenueBoothsRequest(BaseModel):
    booths: list[VenueBoothInput] = Field(
        default_factory=lambda: [], max_length=MAX_LAYOUT_ELEMENTS
    )


class VenueZoneShapeResponse(BaseModel):
    id: UUID
    layout_id: UUID
    booth_zone_id: UUID
    shape: VenueShape
    label_position: VenuePoint | None


class VenueBoothResponse(BaseModel):
    id: UUID
    layout_id: UUID
    booth_zone_id: UUID
    booth_nr: int
    x: float
    y: float
    rotation: float | None


class VenueMapBoothResponse(VenueBoothResponse):
    is_own_booking: bool


class VenueLayoutBase(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    order: int
    width: int
    height: int
    is_active: bool
    floor_plan: KpVenueFloorPlan | None
    background_url: str | None
    background_file: StoredFileResponse | None
    zone_shapes: list[VenueZoneShapeResponse]


class VenueLayoutResult(VenueLayoutBase):
    booths: list[VenueBoothResponse]


class VenueLayoutResponse(VenueLayoutResult):
    pass


class VenueMapLayoutResult(VenueLayoutBase):
    booths: list[VenueMapBoothResponse]


class VenueOwnBookingResult(BaseModel):
    booking_id: UUID
    booth_zone_id: UUID
    booth_nr: int | None


class VenueMapResult(BaseModel):
    event_id: UUID
    layouts: list[VenueMapLayoutResult]
    zones: list[BoothZoneWithAvailabilityResult]
    own_booking: VenueOwnBookingResult | None


class VenueMapResponse(VenueMapResult):
    pass
