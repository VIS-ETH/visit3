from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CsrfDep, KpServiceDep
from app.schemas.kp import (
    BookingUpgradeWaitlistEntryResponse,
    BookingResponse,
    CreateKpRequest,
    KpResponse,
    ReplaceBookingUpgradeWaitlistRequest,
    UpdateBookingBoothNumberRequest,
    UpdateBookingStatusRequest,
)
from app.core.decorators import (
    require_admin,
    require_confirmed_company,
    require_staff,
)

router = APIRouter(prefix="/kp", tags=["kp"], dependencies=[CsrfDep])


@router.get("/list", operation_id="listKps")
async def list_kps(kp_service: KpServiceDep) -> list[KpResponse]:
    return [KpResponse.from_model(event) for event in await kp_service.list_kps()]


@router.get("/latest", operation_id="getLatestKp")
async def get_latest_kp(kp_service: KpServiceDep) -> KpResponse | None:
    event = await kp_service.get_latest_kp()
    return KpResponse.from_model(event) if event is not None else None


@router.get("/name/{name}", operation_id="getKpByName")
async def get_kp_by_name(kp_service: KpServiceDep, name: str) -> KpResponse | None:
    event = await kp_service.get_event_by_name(name)
    return KpResponse.from_model(event) if event is not None else None


@require_confirmed_company
@router.get(
    "/bookings/{booking_id}/upgrade-waitlist",
    operation_id="listBookingUpgradeWaitlist",
)
async def list_booking_upgrade_waitlist(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> list[BookingUpgradeWaitlistEntryResponse]:
    entries = await kp_service.list_booking_upgrade_waitlist(booking_id)
    return [BookingUpgradeWaitlistEntryResponse.from_model(entry) for entry in entries]


@require_confirmed_company
@router.put(
    "/bookings/{booking_id}/upgrade-waitlist",
    operation_id="replaceBookingUpgradeWaitlist",
)
async def replace_booking_upgrade_waitlist(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: ReplaceBookingUpgradeWaitlistRequest,
) -> list[BookingUpgradeWaitlistEntryResponse]:
    entries = await kp_service.replace_booking_upgrade_waitlist(
        booking_id=booking_id,
        target_booth_zone_ids=request.target_booth_zone_ids,
    )
    return [BookingUpgradeWaitlistEntryResponse.from_model(entry) for entry in entries]


@require_confirmed_company
@router.patch("/bookings/{booking_id}/status", operation_id="updateMyBookingStatus")
async def update_my_booking_status(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingStatusRequest,
) -> BookingResponse:
    booking = await kp_service.update_my_booking_status(booking_id, request.status)
    return BookingResponse.from_model(booking)


@require_staff
@router.patch(
    "/bookings/{booking_id}/booth-number",
    operation_id="updateBookingBoothNumber",
)
async def update_booking_booth_number(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingBoothNumberRequest,
) -> BookingResponse:
    booking = await kp_service.update_booking_booth_number(booking_id, request.booth_nr)
    return BookingResponse.from_model(booking)


@require_staff
@router.patch("/bookings/{booking_id}/confirm", operation_id="confirmBooking")
async def confirm_booking(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> BookingResponse:
    booking = await kp_service.confirm_booking(booking_id)
    return BookingResponse.from_model(booking)


@require_admin
@router.post("/create", operation_id="createKp")
async def create_kp(kp_service: KpServiceDep, request: CreateKpRequest) -> KpResponse:
    event = await kp_service.create_kp(
        name=request.name,
        registration_open=request.registration_open,
        registration_end=request.registration_end,
        finalization_deadline=request.finalization_deadline,
        nametags_deadline=request.nametags_deadline,
        event_date=request.event_date,
    )
    return KpResponse.from_model(event)
