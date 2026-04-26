from uuid import UUID

from fastapi import APIRouter, File, UploadFile

from app.core.decorators import (
    require_admin,
    require_confirmed_company,
    require_staff,
)
from app.core.deps import CsrfDep, KpServiceDep
from app.schemas.kp import (
    BookingResponse,
    BookingUpgradeWaitlistEntryResponse,
    CreateKpRequest,
    KpResponse,
    RequirementFileDownloadResponse,
    ReplaceBookingUpgradeWaitlistRequest,
    RequirementFileResponse,
    UpdateBookingBoothNumberRequest,
    UpdateBookingStatusRequest,
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


@router.get(
    "/bookings/{booking_id}/upgrade-waitlist",
    operation_id="listBookingUpgradeWaitlist",
)
@require_confirmed_company
async def list_booking_upgrade_waitlist(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> list[BookingUpgradeWaitlistEntryResponse]:
    entries = await kp_service.list_booking_upgrade_waitlist(booking_id)
    return [BookingUpgradeWaitlistEntryResponse.from_model(entry) for entry in entries]


@router.put(
    "/bookings/{booking_id}/upgrade-waitlist",
    operation_id="replaceBookingUpgradeWaitlist",
)
@require_confirmed_company
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


@router.patch("/bookings/{booking_id}/status", operation_id="updateMyBookingStatus")
@require_confirmed_company
async def update_my_booking_status(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingStatusRequest,
) -> BookingResponse:
    booking = await kp_service.update_my_booking_status(booking_id, request.status)
    return BookingResponse.from_model(booking)


@router.patch(
    "/bookings/{booking_id}/booth-number",
    operation_id="updateBookingBoothNumber",
)
@require_staff
async def update_booking_booth_number(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingBoothNumberRequest,
) -> BookingResponse:
    booking = await kp_service.update_booking_booth_number(booking_id, request.booth_nr)
    return BookingResponse.from_model(booking)


@router.patch("/bookings/{booking_id}/confirm", operation_id="confirmBooking")
@require_staff
async def confirm_booking(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> BookingResponse:
    booking = await kp_service.confirm_booking(booking_id)
    return BookingResponse.from_model(booking)


@router.get(
    "/booking-services/{booking_service_id}/requirements/{requirement_id}/file",
    operation_id="getBookingRequirementFile",
)
@require_confirmed_company
async def get_booking_requirement_file(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
) -> RequirementFileResponse | None:
    requirement_file = await kp_service.get_booking_requirement_file(
        booking_service_id, requirement_id
    )
    return (
        RequirementFileResponse.from_model(requirement_file)
        if requirement_file is not None
        else None
    )


@router.post(
    "/booking-services/{booking_service_id}/requirements/{requirement_id}/file",
    operation_id="uploadBookingRequirementFile",
)
@require_confirmed_company
async def upload_booking_requirement_file(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
    file: UploadFile = File(...),
) -> RequirementFileResponse:
    requirement_file = await kp_service.upload_booking_requirement_file(
        booking_service_id=booking_service_id,
        requirement_id=requirement_id,
        filename=file.filename or "upload.bin",
        content=await file.read(),
        content_type=file.content_type,
    )
    return RequirementFileResponse.from_model(requirement_file)


@router.delete(
    "/booking-services/{booking_service_id}/requirements/{requirement_id}/file",
    operation_id="deleteBookingRequirementFile",
)
@require_confirmed_company
async def delete_booking_requirement_file(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
) -> None:
    await kp_service.delete_booking_requirement_file(booking_service_id, requirement_id)


@router.get(
    "/booking-services/{booking_service_id}/requirements/{requirement_id}/file/download",
    operation_id="getBookingRequirementFileDownloadUrl",
)
@require_confirmed_company
async def get_booking_requirement_file_download_url(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
) -> RequirementFileDownloadResponse:
    url = await kp_service.get_booking_requirement_file_download_url(
        booking_service_id, requirement_id
    )
    return RequirementFileDownloadResponse(url=url)


@router.post("/create", operation_id="createKp")
@require_admin
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
