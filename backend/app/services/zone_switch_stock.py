from app.models.kp_event import (
    UNLIMITED_TOTAL_QUANTITY,
    KpEventBooking,
    KpEventBoothZone,
    KpEventService,
)
from app.repositories.kp_repository import KpRepository


async def service_exceeding_stock(
    kp_repository: KpRepository, booking: KpEventBooking, zone: KpEventBoothZone
) -> KpEventService | None:
    included_quantities = {
        included_service.service_id: included_service.included_quantity
        for included_service in zone.included_services
    }
    package_quantities = await kp_repository.package_inclusion_quantities(
        {
            booking_service.service_id: booking_service.quantity
            for booking_service in booking.services
        }
    )
    for service_id, quantity in package_quantities.items():
        included_quantities[service_id] = (
            included_quantities.get(service_id, 0) + quantity
        )
    for booking_service in booking.services:
        included_quantity = included_quantities.get(booking_service.service_id, 0)
        additional_charged = (
            max(booking_service.quantity - included_quantity, 0)
            - booking_service.charged_quantity
        )
        service = booking_service.service
        if (
            additional_charged <= 0
            or service.max_total_quantity == UNLIMITED_TOTAL_QUANTITY
        ):
            continue
        booked_quantity = await kp_repository.count_active_charged_service_quantity(
            service.id
        )
        if booked_quantity + additional_charged > service.max_total_quantity:
            return service
    return None
