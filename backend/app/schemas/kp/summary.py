from uuid import UUID

from pydantic import BaseModel

from app.models.kp_event import KpBookingStatus, KpServiceCategory
from app.schemas.pricing import PriceBreakdown, VatRatePercent


class BookingTotals(BaseModel):
    count: int
    base: int
    services: int
    price: PriceBreakdown


class BookingStatusTotals(BookingTotals):
    status: KpBookingStatus


class BookingZoneTotals(BookingTotals):
    booth_zone_id: UUID
    name: str
    color: str
    base_price: int
    capacity: int
    occupied: int
    free: int


class BookingServiceTotals(BaseModel):
    service_id: UUID
    name: str
    category: KpServiceCategory
    unit_label: str | None
    unit_price: int
    booking_count: int
    quantity: int
    included_quantity: int
    price: PriceBreakdown
    max_total_quantity: int
    remaining_total_quantity: int | None


class BookingSummaryResponse(BaseModel):
    event_id: UUID
    vat_rate_percent: VatRatePercent
    total: BookingTotals
    by_status: list[BookingStatusTotals]
    offered: BookingTotals
    by_zone: list[BookingZoneTotals]
    by_service: list[BookingServiceTotals]
    capacity: int
    occupied: int
    free: int
    cancelled_count: int
    rejected_count: int
    expired_count: int
