from collections.abc import Sequence

from app.models.kp_event import (
    INACTIVE_BOOKING_STATUSES,
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBoothZone,
)
from app.schemas.kp import (
    BookingStatusTotals,
    BookingSummaryResponse,
    BookingTotals,
    BookingZoneTotals,
)
from app.schemas.pricing import PriceBreakdown
from app.services.booth_zone_view import free_spots
from app.services.pricing import booking_price

ACTIVE_STATUSES = [
    status for status in KpBookingStatus if status not in INACTIVE_BOOKING_STATUSES
]


def booking_totals(
    bookings: Sequence[KpEventBooking], vat_rate_permille: int
) -> BookingTotals:
    prices = [booking_price(booking, vat_rate_permille) for booking in bookings]
    return BookingTotals(
        count=len(bookings),
        base=sum(booking.base_price for booking in bookings),
        services=sum(booking.services_price for booking in bookings),
        price=PriceBreakdown(
            net=sum(price.net for price in prices),
            vat=sum(price.vat for price in prices),
            gross=sum(price.gross for price in prices),
        ),
    )


def zone_totals(
    zone: KpEventBoothZone, bookings: Sequence[KpEventBooking], vat_rate_permille: int
) -> BookingZoneTotals:
    booked = [booking for booking in bookings if booking.booth_zone_id == zone.id]
    return BookingZoneTotals(
        booth_zone_id=zone.id,
        name=zone.name,
        color=zone.color,
        base_price=zone.base_price,
        capacity=zone.capacity,
        free=free_spots(zone.capacity, len(booked)),
        **booking_totals(booked, vat_rate_permille).model_dump(),
    )


def booking_summary(
    event: KpEvent,
    zones: Sequence[KpEventBoothZone],
    bookings: Sequence[KpEventBooking],
) -> BookingSummaryResponse:
    active = [booking for booking in bookings if booking.is_active]
    rate = event.vat_rate_permille
    by_zone = [zone_totals(zone, active, rate) for zone in zones]
    return BookingSummaryResponse(
        event_id=event.id,
        vat_rate_percent=event.vat_rate_percent,
        total=booking_totals(active, rate),
        by_status=[
            BookingStatusTotals(
                status=status,
                **booking_totals(
                    [booking for booking in active if booking.status == status], rate
                ).model_dump(),
            )
            for status in ACTIVE_STATUSES
        ],
        by_zone=by_zone,
        capacity=sum(zone.capacity for zone in by_zone),
        free=sum(zone.free for zone in by_zone),
        cancelled_count=sum(
            booking.status == KpBookingStatus.CANCELLED for booking in bookings
        ),
        rejected_count=sum(
            booking.status == KpBookingStatus.REJECTED for booking in bookings
        ),
    )
