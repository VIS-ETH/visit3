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
from app.services.pricing import price_breakdown

ACTIVE_STATUSES = [
    status for status in KpBookingStatus if status not in INACTIVE_BOOKING_STATUSES
]


def booking_totals(
    bookings: Sequence[KpEventBooking], vat_rate_permille: int
) -> BookingTotals:
    prices = [
        price_breakdown(booking.total_price, vat_rate_permille) for booking in bookings
    ]
    base = sum(booking.booth_zone.base_price for booking in bookings)
    net = sum(price.net for price in prices)
    return BookingTotals(
        count=len(bookings),
        base=base,
        services=net - base,
        price=PriceBreakdown(
            net=net,
            vat=sum(price.vat for price in prices),
            gross=sum(price.gross for price in prices),
        ),
    )


def booking_summary(
    event: KpEvent,
    zones: Sequence[KpEventBoothZone],
    bookings: Sequence[KpEventBooking],
) -> BookingSummaryResponse:
    rate = event.vat_rate_permille
    active = [booking for booking in bookings if booking.is_active]
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
        by_zone=[
            BookingZoneTotals(
                booth_zone_id=zone.id,
                name=zone.name,
                color=zone.color,
                **booking_totals(
                    [booking for booking in active if booking.booth_zone_id == zone.id],
                    rate,
                ).model_dump(),
            )
            for zone in zones
        ],
        cancelled_count=sum(
            booking.status == KpBookingStatus.CANCELLED for booking in bookings
        ),
        rejected_count=sum(
            booking.status == KpBookingStatus.REJECTED for booking in bookings
        ),
    )
