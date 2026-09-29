from collections.abc import Sequence

from app.models.kp_event import (
    BOOKED_STATUSES,
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
    zone: KpEventBoothZone, active: Sequence[KpEventBooking], vat_rate_permille: int
) -> BookingZoneTotals:
    holding = [booking for booking in active if booking.booth_zone_id == zone.id]
    booked = [booking for booking in holding if booking.is_booked]
    return BookingZoneTotals(
        booth_zone_id=zone.id,
        name=zone.name,
        color=zone.color,
        base_price=zone.base_price,
        capacity=zone.capacity,
        occupied=len(holding),
        free=free_spots(zone.capacity, len(holding)),
        **booking_totals(booked, vat_rate_permille).model_dump(),
    )


def count_status(bookings: Sequence[KpEventBooking], status: KpBookingStatus) -> int:
    return sum(booking.status == status for booking in bookings)


def booking_summary(
    event: KpEvent,
    zones: Sequence[KpEventBoothZone],
    bookings: Sequence[KpEventBooking],
) -> BookingSummaryResponse:
    rate = event.vat_rate_permille
    active = [booking for booking in bookings if booking.is_active]
    booked = [booking for booking in active if booking.is_booked]
    offered = [
        booking for booking in active if booking.status == KpBookingStatus.OFFERED
    ]
    by_zone = [zone_totals(zone, active, rate) for zone in zones]
    return BookingSummaryResponse(
        event_id=event.id,
        vat_rate_percent=event.vat_rate_percent,
        total=booking_totals(booked, rate),
        by_status=[
            BookingStatusTotals(
                status=status,
                **booking_totals(
                    [booking for booking in booked if booking.status == status], rate
                ).model_dump(),
            )
            for status in BOOKED_STATUSES
        ],
        offered=booking_totals(offered, rate),
        by_zone=by_zone,
        capacity=sum(zone.capacity for zone in by_zone),
        occupied=sum(zone.occupied for zone in by_zone),
        free=sum(zone.free for zone in by_zone),
        cancelled_count=count_status(bookings, KpBookingStatus.CANCELLED),
        rejected_count=count_status(bookings, KpBookingStatus.REJECTED),
        expired_count=count_status(bookings, KpBookingStatus.EXPIRED),
    )
