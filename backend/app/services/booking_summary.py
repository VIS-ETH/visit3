from collections.abc import Sequence

from app.models.kp_event import (
    BOOKED_STATUSES,
    UNLIMITED_TOTAL_QUANTITY,
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBoothZone,
    KpEventService,
)
from app.schemas.kp import (
    BookingServiceTotals,
    BookingStatusTotals,
    BookingSummaryResponse,
    BookingTotals,
    BookingZoneTotals,
)
from app.schemas.pricing import PriceBreakdown
from app.services.booth_zone_view import free_spots
from app.services.pricing import booking_price, price_breakdown


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


def service_lines(
    service: KpEventService, bookings: Sequence[KpEventBooking]
) -> list[KpEventBookingService]:
    return [
        line
        for booking in bookings
        for line in booking.services
        if line.service_id == service.id
    ]


def service_totals(
    service: KpEventService,
    active: Sequence[KpEventBooking],
    booked: Sequence[KpEventBooking],
    vat_rate_permille: int,
) -> BookingServiceTotals:
    lines = service_lines(service, booked)
    reserved = sum(line.charged_quantity for line in service_lines(service, active))
    limited = service.max_total_quantity != UNLIMITED_TOTAL_QUANTITY
    return BookingServiceTotals(
        service_id=service.id,
        name=service.name,
        category=service.category,
        unit_label=service.unit_label,
        unit_price=service.price,
        booking_count=len(lines),
        quantity=sum(line.charged_quantity for line in lines),
        included_quantity=sum(line.quantity - line.charged_quantity for line in lines),
        price=price_breakdown(sum(line.line_net for line in lines), vat_rate_permille),
        max_total_quantity=service.max_total_quantity,
        remaining_total_quantity=(
            max(service.max_total_quantity - reserved, 0) if limited else None
        ),
    )


def count_status(bookings: Sequence[KpEventBooking], status: KpBookingStatus) -> int:
    return sum(booking.status == status for booking in bookings)


def booking_summary(
    event: KpEvent,
    zones: Sequence[KpEventBoothZone],
    services: Sequence[KpEventService],
    bookings: Sequence[KpEventBooking],
) -> BookingSummaryResponse:
    rate = event.vat_rate_permille
    active = [booking for booking in bookings if booking.is_active]
    booked = [booking for booking in active if booking.is_booked]
    offered = [
        booking for booking in active if booking.status == KpBookingStatus.OFFERED
    ]
    by_zone = [zone_totals(zone, active, rate) for zone in zones]
    by_service = [
        service_totals(service, active, booked, rate)
        for service in services
        if service.is_active or service_lines(service, active)
    ]
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
        by_service=by_service,
        capacity=sum(zone.capacity for zone in by_zone),
        occupied=sum(zone.occupied for zone in by_zone),
        free=sum(zone.free for zone in by_zone),
        cancelled_count=count_status(bookings, KpBookingStatus.CANCELLED),
        rejected_count=count_status(bookings, KpBookingStatus.REJECTED),
        expired_count=count_status(bookings, KpBookingStatus.EXPIRED),
    )
