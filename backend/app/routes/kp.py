from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CsrfDep, KpServiceDep
from app.models.kp_event import KpEvent, KpEventBookingUpgradeWaitlist
from app.schemas.kp import (
    BookingUpgradeWaitlistEntryResponse,
    CreateKpRequest,
    KpResponse,
    ReplaceBookingUpgradeWaitlistRequest,
)
from app.core.decorators import require_admin, require_confirmed_company

router = APIRouter(prefix="/kp", tags=["kp"], dependencies=[CsrfDep])


def _serialize_kp(event: KpEvent) -> KpResponse:
    return KpResponse(
        id=event.id,
        name=event.name,
        registration_open=event.registration_open,
        registration_end=event.registration_end,
        finalization_deadline=event.finalization_deadline,
        nametags_deadline=event.nametags_deadline,
        event_date=event.event_date,
    )


def _serialize_booking_upgrade_waitlist_entry(
    entry: KpEventBookingUpgradeWaitlist,
) -> BookingUpgradeWaitlistEntryResponse:
    return BookingUpgradeWaitlistEntryResponse(
        id=entry.id,
        booking_id=entry.booking_id,
        target_booth_zone_id=entry.target_booth_zone_id,
        target_booth_zone_name=entry.target_booth_zone.name,
        priority_rank=entry.priority_rank,
    )


@router.get("/list", operation_id="listKps")
async def list_kps(kp_service: KpServiceDep) -> list[KpResponse]:
    return [_serialize_kp(event) for event in await kp_service.list_kps()]


@router.get("/latest", operation_id="getLatestKp")
async def get_latest_kp(kp_service: KpServiceDep) -> KpResponse | None:
    event = await kp_service.get_latest_kp()
    return _serialize_kp(event) if event is not None else None


@router.get("/name/{name}", operation_id="getKpByName")
async def get_kp_by_name(kp_service: KpServiceDep, name: str) -> KpResponse | None:
    event = await kp_service.get_event_by_name(name)
    return _serialize_kp(event) if event is not None else None


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
    return [_serialize_booking_upgrade_waitlist_entry(entry) for entry in entries]


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
    return [_serialize_booking_upgrade_waitlist_entry(entry) for entry in entries]


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
    return _serialize_kp(event)
