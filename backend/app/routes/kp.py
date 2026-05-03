from uuid import UUID

from fastapi import APIRouter, File, Query, Response, UploadFile

from app.core.decorators import (
    require_confirmed_company,
    require_kp_president,
)
from app.core.deps import CsrfDep, ExportServiceDep, KpServiceDep
from app.schemas.kp import (
    BookingResponse,
    BookingUpgradeWaitlistEntryResponse,
    BoothZoneResponse,
    CreateBoothZoneRequest,
    CreateIndustryRequest,
    CreateKpRequest,
    CreateServiceRequest,
    ExportBackgroundResponse,
    IndustryResponse,
    KpResponse,
    NametagExportTargetsResponse,
    ReplaceBookingUpgradeWaitlistRequest,
    RequirementFileDownloadResponse,
    RequirementFileResponse,
    ServiceResponse,
    UpdateBookingInput,
    UpdateBoothZoneRequest,
    UpdateKpRequest,
    UpdateServiceRequest,
)

router = APIRouter(prefix="/kp", tags=["kp"], dependencies=[CsrfDep])


def _pdf_download(content: bytes, filename: str) -> Response:
    return _download(content, filename, "application/pdf")


def _csv_download(content: bytes, filename: str) -> Response:
    return _download(content, filename, "text/csv; charset=utf-8")


def _zip_download(content: bytes, filename: str) -> Response:
    return _download(content, filename, "application/zip")


def _download(content: bytes, filename: str, media_type: str) -> Response:
    safe_filename = filename.replace('"', "").replace("/", "-")
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
        },
    )


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
async def delete_booth_zone(kp_service: KpServiceDep, booth_zone_id: UUID) -> None:
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
@router.post(
    "/industries", operation_id="createIndustry", response_model=IndustryResponse
)
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
    response_model=RequirementFileResponse | None,
)
async def get_booking_requirement_file(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
) -> RequirementFileResponse | None:
    return await kp_service.get_booking_requirement_file(
        booking_service_id, requirement_id
    )


@router.post(
    "/booking-services/{booking_service_id}/requirements/{requirement_id}/file",
    operation_id="uploadBookingRequirementFile",
    response_model=RequirementFileResponse,
)
async def upload_booking_requirement_file(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
    file: UploadFile = File(...),
) -> RequirementFileResponse:
    return await kp_service.upload_booking_requirement_file(
        booking_service_id=booking_service_id,
        requirement_id=requirement_id,
        filename=file.filename or "upload.bin",
        content=await file.read(),
        content_type=file.content_type,
    )


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


# --- Exports ---


@router.post(
    "/events/{event_id}/exports/nametags/background",
    operation_id="uploadNametagExportBackground",
    response_model=ExportBackgroundResponse,
)
async def upload_nametag_export_background(
    export_service: ExportServiceDep,
    event_id: UUID,
    file: UploadFile = File(...),
) -> ExportBackgroundResponse:
    return await export_service.upload_nametag_background(
        event_id=event_id,
        filename=file.filename or "nametag-background",
        content=await file.read(),
        content_type=file.content_type,
    )


@router.get(
    "/events/{event_id}/exports/nametags/background",
    operation_id="getNametagExportBackground",
    response_model=ExportBackgroundResponse | None,
)
async def get_nametag_export_background(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> ExportBackgroundResponse | None:
    return await export_service.get_nametag_background(event_id)


@router.get(
    "/events/{event_id}/exports/nametags/targets",
    operation_id="listNametagExportTargets",
    response_model=NametagExportTargetsResponse,
)
async def list_nametag_export_targets(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> NametagExportTargetsResponse:
    return await export_service.list_nametag_export_targets(event_id)


@router.get(
    "/events/{event_id}/exports/nametags/download",
    operation_id="downloadEventNametags",
)
async def download_event_nametags(
    export_service: ExportServiceDep,
    event_id: UUID,
    columns: int | None = Query(default=None, ge=1, le=10),
) -> Response:
    export = await export_service.render_event_nametags(event_id, columns)
    return _pdf_download(export.content, export.filename)


@router.get(
    "/bookings/{booking_id}/nametags/download",
    operation_id="downloadBookingNametags",
)
async def download_booking_nametags(
    export_service: ExportServiceDep,
    booking_id: UUID,
    columns: int | None = Query(default=None, ge=1, le=10),
) -> Response:
    export = await export_service.render_booking_nametags(booking_id, columns)
    return _pdf_download(export.content, export.filename)


@router.get(
    "/nametags/{name_tag_id}/download",
    operation_id="downloadSingleNametag",
)
async def download_single_nametag(
    export_service: ExportServiceDep,
    name_tag_id: UUID,
) -> Response:
    export = await export_service.render_single_nametag(name_tag_id)
    return _pdf_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/bookings/download",
    operation_id="downloadEventBookingsCsv",
)
async def download_event_bookings_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_bookings_csv(event_id)
    return _csv_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/bookings/by-zone/download",
    operation_id="downloadEventBookingsByZoneZip",
)
async def download_event_bookings_by_zone_zip(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_bookings_by_zone_zip(event_id)
    return _zip_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/waitlist-companies/download",
    operation_id="downloadEventWaitlistCompaniesCsv",
)
async def download_event_waitlist_companies_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_waitlist_companies_csv(event_id)
    return _csv_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/booked-services/download",
    operation_id="downloadEventBookedServicesCsv",
)
async def download_event_booked_services_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_booked_services_csv(event_id)
    return _csv_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/nametags-data/download",
    operation_id="downloadEventNametagsDataCsv",
)
async def download_event_nametags_data_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_nametags_data_csv(event_id)
    return _csv_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/company-details/download",
    operation_id="downloadEventCompanyDetailsCsv",
)
async def download_event_company_details_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_company_details_csv(event_id)
    return _csv_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/service-requirements/download",
    operation_id="downloadEventServiceRequirementsCsv",
)
async def download_event_service_requirements_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_service_requirements_csv(event_id)
    return _csv_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/booth-zone-capacity/download",
    operation_id="downloadEventBoothZoneCapacityCsv",
)
async def download_event_booth_zone_capacity_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_booth_zone_capacity_csv(event_id)
    return _csv_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/contacts/download",
    operation_id="downloadEventContactsCsv",
)
async def download_event_contacts_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_contacts_csv(event_id)
    return _csv_download(export.content, export.filename)


@router.get(
    "/events/{event_id}/exports/registration-exceptions/download",
    operation_id="downloadEventRegistrationExceptionsCsv",
)
async def download_event_registration_exceptions_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_registration_exceptions_csv(event_id)
    return _csv_download(export.content, export.filename)
