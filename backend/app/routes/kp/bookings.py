from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import KpServiceDep
from app.models.kp_event import KpServiceCategory
from app.schemas.kp import (
    AcceptOfferRequest,
    AddBookingServicesRequest,
    BookingResponse,
    BookingSummaryResponse,
    BookingUpgradeWaitlistEntryResponse,
    BookingUpgradeWaitlistEntryResult,
    BookingWithCompanyAndBoothZoneResponse,
    BoothZoneWithAvailabilityResponse,
    BoothZoneWithAvailabilityResult,
    MyBookingResponse,
    NameTagResponse,
    NameTagResult,
    OfferBookingRequest,
    RegisterBookingRequest,
    RejectBookingRequest,
    ReplaceBookingUpgradeWaitlistRequest,
    ReplaceNameTagsRequest,
    ServiceResponse,
    StaffBookingResponse,
    StaffBookingUpgradeWaitlistEntryResponse,
    StaffBookingUpgradeWaitlistEntryResult,
    StaffUpdateBookingRequest,
    SwitchBookingZoneRequest,
    UpdateBookingBoothNumberRequest,
    UpdateBookingOfferRequest,
    UpdateBookingStatusRequest,
)

router = APIRouter()


@router.get(
    "/events/{event_id}/booth-zones/available",
    operation_id="listAvailableBoothZones",
    response_model=list[BoothZoneWithAvailabilityResponse],
)
async def list_available_booth_zones(
    kp_service: KpServiceDep, event_id: UUID
) -> list[BoothZoneWithAvailabilityResult]:
    return await kp_service.list_booth_zones_for_company(event_id)


@router.post(
    "/events/{event_id}/bookings/register",
    operation_id="registerBooking",
    response_model=BookingResponse,
)
async def register_booking(
    kp_service: KpServiceDep, event_id: UUID, request: RegisterBookingRequest
) -> BookingResponse:
    return await kp_service.register_booking(
        event_id, request.booth_zone_id, request.services, request.confirm_profile
    )


@router.get(
    "/events/{event_id}/services/available",
    operation_id="listAvailableServices",
    response_model=list[ServiceResponse],
)
async def list_available_services(
    kp_service: KpServiceDep,
    event_id: UUID,
    category: KpServiceCategory | None = Query(default=None),
) -> list[ServiceResponse]:
    return await kp_service.list_available_services_for_company(event_id, category)


@router.get(
    "/events/{event_id}/my-booking",
    operation_id="getMyBooking",
    response_model=MyBookingResponse | None,
)
async def get_my_booking(
    kp_service: KpServiceDep, event_id: UUID
) -> MyBookingResponse | None:
    return await kp_service.get_my_booking(event_id)


@router.post(
    "/bookings/{booking_id}/services",
    operation_id="addBookingServices",
    response_model=BookingResponse,
)
async def add_booking_services(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: AddBookingServicesRequest,
) -> BookingResponse:
    return await kp_service.add_booking_services(booking_id, request.services)


@router.get(
    "/events/{event_id}/bookings",
    operation_id="listEventBookings",
    response_model=list[StaffBookingResponse],
)
async def list_event_bookings(
    kp_service: KpServiceDep, event_id: UUID
) -> list[BookingWithCompanyAndBoothZoneResponse]:
    return await kp_service.list_bookings_for_event(event_id)


@router.get(
    "/events/{event_id}/bookings/summary",
    operation_id="getBookingsSummary",
    response_model=BookingSummaryResponse,
)
async def get_bookings_summary(
    kp_service: KpServiceDep, event_id: UUID
) -> BookingSummaryResponse:
    return await kp_service.get_bookings_summary(event_id)


@router.get(
    "/events/{event_id}/bookings/{booking_id}",
    operation_id="getEventBooking",
    response_model=StaffBookingResponse,
)
async def get_event_booking(
    kp_service: KpServiceDep, event_id: UUID, booking_id: UUID
) -> BookingWithCompanyAndBoothZoneResponse:
    return await kp_service.get_event_booking(event_id, booking_id)


@router.get(
    "/bookings/{booking_id}/upgrade-waitlist",
    operation_id="listBookingUpgradeWaitlist",
    response_model=list[BookingUpgradeWaitlistEntryResponse],
)
async def list_booking_upgrade_waitlist(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> list[BookingUpgradeWaitlistEntryResult]:
    return await kp_service.list_booking_upgrade_waitlist(booking_id)


@router.put(
    "/bookings/{booking_id}/upgrade-waitlist",
    operation_id="replaceBookingUpgradeWaitlist",
    response_model=list[BookingUpgradeWaitlistEntryResponse],
)
async def replace_booking_upgrade_waitlist(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: ReplaceBookingUpgradeWaitlistRequest,
) -> list[BookingUpgradeWaitlistEntryResult]:
    return await kp_service.replace_booking_upgrade_waitlist(
        booking_id=booking_id,
        target_booth_zone_ids=request.target_booth_zone_ids,
    )


@router.post(
    "/bookings/{booking_id}/switch-zone",
    operation_id="switchBookingZone",
    response_model=BookingResponse,
)
async def switch_booking_zone(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: SwitchBookingZoneRequest,
) -> BookingResponse:
    return await kp_service.switch_booking_zone(booking_id, request.booth_zone_id)


@router.get(
    "/bookings/{booking_id}/nametags",
    operation_id="listBookingNametags",
    response_model=list[NameTagResponse],
)
async def list_booking_nametags(
    kp_service: KpServiceDep, booking_id: UUID
) -> list[NameTagResult]:
    return await kp_service.list_booking_name_tags(booking_id)


@router.put(
    "/bookings/{booking_id}/nametags",
    operation_id="replaceBookingNametags",
    response_model=list[NameTagResponse],
)
async def replace_booking_nametags(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: ReplaceNameTagsRequest,
) -> list[NameTagResult]:
    return await kp_service.replace_booking_name_tags(booking_id, request.name_tags)


@router.get(
    "/staff/bookings/{booking_id}/nametags",
    operation_id="listStaffBookingNametags",
    response_model=list[NameTagResponse],
)
async def list_staff_booking_nametags(
    kp_service: KpServiceDep, booking_id: UUID
) -> list[NameTagResult]:
    return await kp_service.list_booking_name_tags_for_staff(booking_id)


@router.get(
    "/staff/bookings/{booking_id}/upgrade-waitlist",
    operation_id="listStaffBookingUpgradeWaitlist",
    response_model=list[StaffBookingUpgradeWaitlistEntryResponse],
)
async def list_staff_booking_upgrade_waitlist(
    kp_service: KpServiceDep, booking_id: UUID
) -> list[StaffBookingUpgradeWaitlistEntryResult]:
    return await kp_service.list_booking_upgrade_waitlist_for_staff(booking_id)


@router.patch(
    "/bookings/{booking_id}/status",
    operation_id="updateMyBookingStatus",
    response_model=BookingResponse,
)
async def update_my_booking_status(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingStatusRequest,
) -> BookingResponse:
    return await kp_service.update_my_booking_status(booking_id, request)


@router.patch(
    "/bookings/{booking_id}/booth-number",
    operation_id="updateBookingBoothNumber",
    response_model=StaffBookingResponse,
)
async def update_booking_booth_number(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingBoothNumberRequest,
) -> BookingWithCompanyAndBoothZoneResponse:
    return await kp_service.update_booking_booth_number(booking_id, request)


@router.post(
    "/bookings/{booking_id}/accept",
    operation_id="acceptBooking",
    response_model=StaffBookingResponse,
)
async def accept_booking(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> BookingWithCompanyAndBoothZoneResponse:
    return await kp_service.accept_booking(booking_id)


@router.post(
    "/bookings/{booking_id}/acknowledge-additions",
    operation_id="acknowledgeBookingAdditions",
    response_model=StaffBookingResponse,
)
async def acknowledge_booking_additions(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> BookingWithCompanyAndBoothZoneResponse:
    return await kp_service.acknowledge_booking_additions(booking_id)


@router.post(
    "/bookings/{booking_id}/undo-accept",
    operation_id="undoAcceptBooking",
    response_model=StaffBookingResponse,
)
async def undo_accept_booking(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> BookingWithCompanyAndBoothZoneResponse:
    return await kp_service.undo_accept_booking(booking_id)


@router.post(
    "/bookings/{booking_id}/reject",
    operation_id="rejectBooking",
    response_model=StaffBookingResponse,
)
async def reject_booking(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: RejectBookingRequest,
) -> BookingWithCompanyAndBoothZoneResponse:
    return await kp_service.reject_booking(booking_id, request)


@router.patch(
    "/bookings/{booking_id}",
    operation_id="updateBooking",
    response_model=StaffBookingResponse,
)
async def update_booking(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: StaffUpdateBookingRequest,
) -> BookingWithCompanyAndBoothZoneResponse:
    return await kp_service.update_booking(booking_id, request)


@router.post(
    "/events/{event_id}/bookings/offer",
    operation_id="offerBooking",
    response_model=StaffBookingResponse,
)
async def offer_booking(
    kp_service: KpServiceDep, event_id: UUID, request: OfferBookingRequest
) -> BookingWithCompanyAndBoothZoneResponse:
    return await kp_service.offer_booking(event_id, request)


@router.patch(
    "/bookings/{booking_id}/offer",
    operation_id="updateBookingOffer",
    response_model=StaffBookingResponse,
)
async def update_booking_offer(
    kp_service: KpServiceDep, booking_id: UUID, request: UpdateBookingOfferRequest
) -> BookingWithCompanyAndBoothZoneResponse:
    return await kp_service.update_booking_offer(booking_id, request)


@router.post(
    "/bookings/{booking_id}/accept-offer",
    operation_id="acceptBookingOffer",
    response_model=BookingResponse,
)
async def accept_booking_offer(
    kp_service: KpServiceDep, booking_id: UUID, request: AcceptOfferRequest
) -> BookingResponse:
    return await kp_service.accept_offer(booking_id, request)


@router.delete("/bookings/{booking_id}", operation_id="deleteBooking")
async def delete_booking(
    kp_service: KpServiceDep,
    booking_id: UUID,
    force: bool = Query(default=False),
) -> None:
    await kp_service.delete_booking(booking_id, force)
