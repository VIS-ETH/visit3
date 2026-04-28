from uuid import UUID

from fastapi import APIRouter, File, UploadFile

from app.core.deps import CsrfDep, KpServiceDep
from app.schemas.kp import (
    BookingResponse,
    BookingUpgradeWaitlistEntryResponse,
    BoothZoneResponse,
    CreateBoothZoneRequest,
    CreateIndustryRequest,
    CreateKpRequest,
    CreateServiceRequest,
    IndustryResponse,
    KpResponse,
    RequirementFileDownloadResponse,
    ReplaceBookingUpgradeWaitlistRequest,
    ServiceResponse,
    RequirementFileResponse,
    UpdateBookingInput,
    UpdateBoothZoneRequest,
    UpdateKpRequest,
    UpdateServiceRequest,
)
from app.core.decorators import (
    require_confirmed_company,
    require_kp_president,
)

router = APIRouter(prefix="/kp", tags=["kp"], dependencies=[CsrfDep])


# --- KP Events ---


@router.get("/list", operation_id="listKps", response_model=list[KpResponse])
async def list_kps(kp_service: KpServiceDep) -> list[KpResponse]:
    return await kp_service.list_kps()


@router.get("/latest", operation_id="getLatestKp", response_model=KpResponse | None)
async def get_latest_kp(kp_service: KpServiceDep) -> KpResponse | None:
    return await kp_service.get_latest_kp()


@require_kp_president
@router.get("/events/{event_id}", operation_id="getKpById", response_model=KpResponse)
async def get_kp_by_id(kp_service: KpServiceDep, event_id: UUID) -> KpResponse:
    return await kp_service.get_event_by_id(event_id)


@require_kp_president
@router.post("/create", operation_id="createKp", response_model=KpResponse)
async def create_kp(kp_service: KpServiceDep, request: CreateKpRequest) -> KpResponse:
    return await kp_service.create_kp(request)


@require_kp_president
@router.patch("/events/{event_id}", operation_id="updateKp", response_model=KpResponse)
async def update_kp(
    kp_service: KpServiceDep, event_id: UUID, request: UpdateKpRequest
) -> KpResponse:
    return await kp_service.update_kp(event_id, request)


# --- Booth Zones ---


@require_kp_president
@router.get(
    "/events/{event_id}/booth-zones",
    operation_id="listBoothZones",
    response_model=list[BoothZoneResponse],
)
async def list_booth_zones(
    kp_service: KpServiceDep, event_id: UUID
) -> list[BoothZoneResponse]:
    return await kp_service.list_booth_zones(event_id)


@require_kp_president
@router.post(
    "/events/{event_id}/booth-zones",
    operation_id="createBoothZone",
    response_model=BoothZoneResponse,
)
async def create_booth_zone(
    kp_service: KpServiceDep, event_id: UUID, request: CreateBoothZoneRequest
) -> BoothZoneResponse:
    return await kp_service.create_booth_zone(event_id, request)


@require_kp_president
@router.patch(
    "/booth-zones/{booth_zone_id}",
    operation_id="updateBoothZone",
    response_model=BoothZoneResponse,
)
async def update_booth_zone(
    kp_service: KpServiceDep,
    booth_zone_id: UUID,
    request: UpdateBoothZoneRequest,
) -> BoothZoneResponse:
    return await kp_service.update_booth_zone(booth_zone_id, request)


@require_kp_president
@router.delete("/booth-zones/{booth_zone_id}", operation_id="deleteBoothZone")
async def delete_booth_zone(
    kp_service: KpServiceDep, booth_zone_id: UUID
) -> None:
    await kp_service.delete_booth_zone(booth_zone_id)


# --- Services ---


@require_kp_president
@router.get(
    "/events/{event_id}/services",
    operation_id="listServices",
    response_model=list[ServiceResponse],
)
async def list_services(
    kp_service: KpServiceDep, event_id: UUID
) -> list[ServiceResponse]:
    return await kp_service.list_services(event_id)


@require_kp_president
@router.post(
    "/events/{event_id}/services",
    operation_id="createService",
    response_model=ServiceResponse,
)
async def create_service(
    kp_service: KpServiceDep, event_id: UUID, request: CreateServiceRequest
) -> ServiceResponse:
    return await kp_service.create_service(event_id, request)


@require_kp_president
@router.patch(
    "/services/{service_id}",
    operation_id="updateService",
    response_model=ServiceResponse,
)
async def update_service(
    kp_service: KpServiceDep,
    service_id: UUID,
    request: UpdateServiceRequest,
) -> ServiceResponse:
    return await kp_service.update_service(service_id, request)


@require_kp_president
@router.delete("/services/{service_id}", operation_id="deleteService")
async def delete_service(kp_service: KpServiceDep, service_id: UUID) -> None:
    await kp_service.delete_service(service_id)


# --- Industries ---


@require_kp_president
@router.get(
    "/industries", operation_id="listIndustries", response_model=list[IndustryResponse]
)
async def list_industries(kp_service: KpServiceDep) -> list[IndustryResponse]:
    return await kp_service.list_industries()


@require_kp_president
@router.post("/industries", operation_id="createIndustry", response_model=IndustryResponse)
async def create_industry(
    kp_service: KpServiceDep, request: CreateIndustryRequest
) -> IndustryResponse:
    return await kp_service.create_industry(request)


@require_kp_president
@router.delete("/industries/{industry_id}", operation_id="deleteIndustry")
async def delete_industry(kp_service: KpServiceDep, industry_id: UUID) -> None:
    await kp_service.delete_industry(industry_id)


# --- Bookings ---


@require_kp_president
@router.get(
    "/events/{event_id}/bookings",
    operation_id="listEventBookings",
    response_model=list[BookingResponse],
)
async def list_event_bookings(
    kp_service: KpServiceDep, event_id: UUID
) -> list[BookingResponse]:
    return await kp_service.list_bookings_for_event(event_id)


@router.get(
    "/bookings/{booking_id}/upgrade-waitlist",
    operation_id="listBookingUpgradeWaitlist",
    response_model=list[BookingUpgradeWaitlistEntryResponse],
)
async def list_booking_upgrade_waitlist(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> list[BookingUpgradeWaitlistEntryResponse]:
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
) -> list[BookingUpgradeWaitlistEntryResponse]:
    return await kp_service.replace_booking_upgrade_waitlist(
        booking_id=booking_id,
        target_booth_zone_ids=request.target_booth_zone_ids,
    )


@require_confirmed_company
@router.patch(
    "/bookings/{booking_id}/status",
    operation_id="updateMyBookingStatus",
    response_model=BookingResponse,
)
async def update_my_booking_status(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingInput,
) -> BookingResponse:
    return await kp_service.update_my_booking_status(booking_id, request)


@require_kp_president
@router.patch(
    "/bookings/{booking_id}/booth-number",
    operation_id="updateBookingBoothNumber",
    response_model=BookingResponse,
)
async def update_booking_booth_number(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingInput,
) -> BookingResponse:
    return await kp_service.update_booking_booth_number(booking_id, request)


@require_kp_president
@router.patch(
    "/bookings/{booking_id}/confirm",
    operation_id="confirmBooking",
    response_model=BookingResponse,
)
async def confirm_booking(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> BookingResponse:
    return await kp_service.confirm_booking(booking_id)


@router.get(
    "/booking-services/{booking_service_id}/requirements/{requirement_id}/file",
    operation_id="getBookingRequirementFile",
)
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
async def get_booking_requirement_file_download_url(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
) -> RequirementFileDownloadResponse:
    url = await kp_service.get_booking_requirement_file_download_url(
        booking_service_id, requirement_id
    )
    return RequirementFileDownloadResponse(url=url)


