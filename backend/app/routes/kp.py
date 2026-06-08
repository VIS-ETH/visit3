from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, File, Query, Response, UploadFile

from app.core.deps import CsrfDep, ExportServiceDep, KpServiceDep
from app.core.downloads import content_disposition_attachment
from app.models.kp_event import (
    KpEvent,
    KpEventBooking,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventNametagBackground,
    KpIndustry,
)
from app.schemas.kp import (
    BookingRequirementFileMapResponse,
    BookingResponse,
    BookingUpgradeWaitlistEntryResponse,
    BookingWithCompanyAndBoothZoneResponse,
    BoothZoneResponse,
    BoothZoneWithAvailabilityResponse,
    BoothZoneWithAvailabilityResult,
    CloneKpRequest,
    CreateBoothZoneRequest,
    CreateIndustryRequest,
    CreateKpRequest,
    CreateServiceRequest,
    ExportBackgroundResponse,
    IndustryResponse,
    KpResponse,
    NametagExportTargetsResponse,
    NametagExportTargetsResult,
    RegisterBookingRequest,
    ReplaceBookingUpgradeWaitlistRequest,
    RequirementFileDownloadResponse,
    RequirementFileResponse,
    RequirementTextRequest,
    RequirementTextResponse,
    ServiceResponse,
    UpdateBookingBoothNumberRequest,
    UpdateBookingStatusRequest,
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
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": content_disposition_attachment(filename),
        },
    )


# --- KP Events ---


@router.get("/list", operation_id="listKps", response_model=list[KpResponse])
async def list_kps(kp_service: KpServiceDep) -> Sequence[KpEvent]:
    return await kp_service.list_kps()


@router.get("/latest", operation_id="getLatestKp", response_model=KpResponse | None)
async def get_latest_kp(kp_service: KpServiceDep) -> KpEvent | None:
    return await kp_service.get_latest_kp()


@router.get("/events/{event_id}", operation_id="getKpById", response_model=KpResponse)
async def get_kp_by_id(kp_service: KpServiceDep, event_id: UUID) -> KpEvent:
    return await kp_service.get_event_by_id(event_id)


@router.post("/create", operation_id="createKp", response_model=KpResponse)
async def create_kp(kp_service: KpServiceDep, request: CreateKpRequest) -> KpEvent:
    return await kp_service.create_kp(request)


@router.patch("/events/{event_id}", operation_id="updateKp", response_model=KpResponse)
async def update_kp(
    kp_service: KpServiceDep, event_id: UUID, request: UpdateKpRequest
) -> KpEvent:
    return await kp_service.update_kp(event_id, request)


@router.post(
    "/events/{event_id}/clone",
    operation_id="cloneKp",
    response_model=KpResponse,
)
async def clone_kp(
    kp_service: KpServiceDep, event_id: UUID, request: CloneKpRequest
) -> KpEvent:
    return await kp_service.clone_kp(event_id, request)


# --- Booth Zones ---


@router.get(
    "/events/{event_id}/booth-zones",
    operation_id="listBoothZones",
    response_model=list[BoothZoneResponse],
)
async def list_booth_zones(
    kp_service: KpServiceDep, event_id: UUID
) -> Sequence[KpEventBoothZone]:
    return await kp_service.list_booth_zones(event_id)


@router.post(
    "/events/{event_id}/booth-zones",
    operation_id="createBoothZone",
    response_model=BoothZoneResponse,
)
async def create_booth_zone(
    kp_service: KpServiceDep, event_id: UUID, request: CreateBoothZoneRequest
) -> KpEventBoothZone:
    return await kp_service.create_booth_zone(event_id, request)


@router.patch(
    "/booth-zones/{booth_zone_id}",
    operation_id="updateBoothZone",
    response_model=BoothZoneResponse,
)
async def update_booth_zone(
    kp_service: KpServiceDep,
    booth_zone_id: UUID,
    request: UpdateBoothZoneRequest,
) -> KpEventBoothZone:
    return await kp_service.update_booth_zone(booth_zone_id, request)


@router.delete("/booth-zones/{booth_zone_id}", operation_id="deleteBoothZone")
async def delete_booth_zone(kp_service: KpServiceDep, booth_zone_id: UUID) -> None:
    await kp_service.delete_booth_zone(booth_zone_id)


# --- Services ---


@router.get(
    "/events/{event_id}/services",
    operation_id="listServices",
    response_model=list[ServiceResponse],
)
async def list_services(
    kp_service: KpServiceDep, event_id: UUID
) -> list[ServiceResponse]:
    return await kp_service.list_services(event_id)


@router.post(
    "/events/{event_id}/services",
    operation_id="createService",
    response_model=ServiceResponse,
)
async def create_service(
    kp_service: KpServiceDep, event_id: UUID, request: CreateServiceRequest
) -> ServiceResponse:
    return await kp_service.create_service(event_id, request)


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


@router.delete("/services/{service_id}", operation_id="deleteService")
async def delete_service(kp_service: KpServiceDep, service_id: UUID) -> None:
    await kp_service.delete_service(service_id)


@router.post(
    "/services/{service_id}/image",
    operation_id="uploadServiceImage",
    response_model=ServiceResponse,
)
async def upload_service_image(
    kp_service: KpServiceDep,
    service_id: UUID,
    file: UploadFile = File(...),
) -> ServiceResponse:
    return await kp_service.upload_service_image(
        service_id=service_id,
        filename=file.filename or "service-image",
        content=await file.read(),
        content_type=file.content_type,
    )


@router.delete(
    "/services/{service_id}/image",
    operation_id="deleteServiceImage",
    response_model=ServiceResponse,
)
async def delete_service_image(
    kp_service: KpServiceDep,
    service_id: UUID,
) -> ServiceResponse:
    return await kp_service.delete_service_image(service_id)


# --- Industries ---


@router.get(
    "/industries", operation_id="listIndustries", response_model=list[IndustryResponse]
)
async def list_industries(kp_service: KpServiceDep) -> Sequence[KpIndustry]:
    return await kp_service.list_industries()


@router.post(
    "/industries", operation_id="createIndustry", response_model=IndustryResponse
)
async def create_industry(
    kp_service: KpServiceDep, request: CreateIndustryRequest
) -> KpIndustry:
    return await kp_service.create_industry(request)


@router.delete("/industries/{industry_id}", operation_id="deleteIndustry")
async def delete_industry(kp_service: KpServiceDep, industry_id: UUID) -> None:
    await kp_service.delete_industry(industry_id)


# --- Company Booking Flow ---


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
        event_id, request.booth_zone_id, request.services
    )


@router.get(
    "/events/{event_id}/services/available",
    operation_id="listAvailableServices",
    response_model=list[ServiceResponse],
)
async def list_available_services(
    kp_service: KpServiceDep, event_id: UUID
) -> list[ServiceResponse]:
    return await kp_service.list_available_services_for_company(event_id)


@router.get(
    "/events/{event_id}/my-booking",
    operation_id="getMyBooking",
    response_model=BookingResponse | None,
)
async def get_my_booking(
    kp_service: KpServiceDep, event_id: UUID
) -> BookingResponse | None:
    return await kp_service.get_my_booking(event_id)


# --- Bookings ---


@router.get(
    "/events/{event_id}/bookings",
    operation_id="listEventBookings",
    response_model=list[BookingWithCompanyAndBoothZoneResponse],
)
async def list_event_bookings(
    kp_service: KpServiceDep, event_id: UUID
) -> Sequence[KpEventBooking]:
    return await kp_service.list_bookings_for_event(event_id)


@router.get(
    "/events/{event_id}/bookings/{booking_id}",
    operation_id="getEventBooking",
    response_model=BookingWithCompanyAndBoothZoneResponse,
)
async def get_event_booking(
    kp_service: KpServiceDep, event_id: UUID, booking_id: UUID
) -> KpEventBooking:
    return await kp_service.get_event_booking(event_id, booking_id)


@router.get(
    "/bookings/{booking_id}/upgrade-waitlist",
    operation_id="listBookingUpgradeWaitlist",
    response_model=list[BookingUpgradeWaitlistEntryResponse],
)
async def list_booking_upgrade_waitlist(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> Sequence[KpEventBookingUpgradeWaitlist]:
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
) -> Sequence[KpEventBookingUpgradeWaitlist]:
    return await kp_service.replace_booking_upgrade_waitlist(
        booking_id=booking_id,
        target_booth_zone_ids=request.target_booth_zone_ids,
    )


@router.patch(
    "/bookings/{booking_id}/status",
    operation_id="updateMyBookingStatus",
    response_model=BookingWithCompanyAndBoothZoneResponse,
)
async def update_my_booking_status(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingStatusRequest,
) -> KpEventBooking:
    return await kp_service.update_my_booking_status(booking_id, request)


@router.patch(
    "/bookings/{booking_id}/booth-number",
    operation_id="updateBookingBoothNumber",
    response_model=BookingWithCompanyAndBoothZoneResponse,
)
async def update_booking_booth_number(
    kp_service: KpServiceDep,
    booking_id: UUID,
    request: UpdateBookingBoothNumberRequest,
) -> KpEventBooking:
    return await kp_service.update_booking_booth_number(booking_id, request)


@router.patch(
    "/bookings/{booking_id}/confirm",
    operation_id="confirmBooking",
    response_model=BookingWithCompanyAndBoothZoneResponse,
)
async def confirm_booking(
    kp_service: KpServiceDep,
    booking_id: UUID,
) -> KpEventBooking:
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
) -> KpEventBookingServiceFileLink | None:
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
) -> KpEventBookingServiceFileLink:
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


@router.put(
    "/booking-services/{booking_service_id}/requirements/{requirement_id}/text",
    operation_id="upsertBookingRequirementText",
    response_model=RequirementTextResponse,
)
async def upsert_booking_requirement_text(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
    request: RequirementTextRequest,
) -> RequirementTextResponse:
    return await kp_service.upsert_booking_requirement_text(
        booking_service_id, requirement_id, request.text_value
    )


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


@router.get(
    "/staff/booking-services/{booking_service_id}/requirements/{requirement_id}/file",
    operation_id="getStaffBookingRequirementFile",
    response_model=RequirementFileResponse | None,
)
async def get_staff_booking_requirement_file(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
) -> KpEventBookingServiceFileLink | None:
    return await kp_service.get_staff_booking_requirement_file(
        booking_service_id, requirement_id
    )


@router.get(
    "/staff/booking-services/{booking_service_id}/requirements/{requirement_id}/file/download",
    operation_id="getStaffBookingRequirementFileDownloadUrl",
)
async def get_staff_booking_requirement_file_download_url(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
) -> RequirementFileDownloadResponse:
    url = await kp_service.get_staff_booking_requirement_file_download_url(
        booking_service_id, requirement_id
    )
    return RequirementFileDownloadResponse(url=url)


@router.get(
    "/staff/events/{event_id}/bookings/{booking_id}/requirement-files",
    operation_id="listStaffBookingRequirementFiles",
    response_model=BookingRequirementFileMapResponse,
)
async def list_staff_booking_requirement_files(
    kp_service: KpServiceDep,
    event_id: UUID,
    booking_id: UUID,
) -> BookingRequirementFileMapResponse:
    return await kp_service.list_staff_booking_requirement_files(event_id, booking_id)


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
) -> KpEventNametagBackground:
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
) -> KpEventNametagBackground | None:
    return await export_service.get_nametag_background(event_id)


@router.get(
    "/events/{event_id}/exports/nametags/targets",
    operation_id="listNametagExportTargets",
    response_model=NametagExportTargetsResponse,
)
async def list_nametag_export_targets(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> NametagExportTargetsResult:
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
