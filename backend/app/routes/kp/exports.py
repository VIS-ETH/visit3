from uuid import UUID

from fastapi import APIRouter, File, Query, Request, Response, UploadFile

from app.core.config import get_settings
from app.core.deps import ExportServiceDep
from app.core.downloads import content_disposition_attachment
from app.core.rate_limit import user_rate_limit
from app.core.uploads import upload_size
from app.models.kp_event import KpEventNametagBackground
from app.schemas.kp import (
    ExportBackgroundResponse,
    NametagExportTargetsResponse,
    NametagExportTargetsResult,
    NametagPreviewResponse,
    NametagPreviewResult,
)
from app.services.company_workbook import ExportLanguage

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

router = APIRouter()


def _pdf_download(content: bytes, filename: str) -> Response:
    return _download(content, filename, "application/pdf")


def _csv_download(content: bytes, filename: str) -> Response:
    return _download(content, filename, "text/csv; charset=utf-8")


def _xlsx_download(content: bytes, filename: str) -> Response:
    return _download(content, filename, XLSX_MEDIA_TYPE)


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


@router.post(
    "/events/{event_id}/exports/nametags/background",
    operation_id="uploadNametagExportBackground",
    response_model=ExportBackgroundResponse,
)
async def upload_nametag_export_background(
    export_service: ExportServiceDep,
    request: Request,
    event_id: UUID,
    file: UploadFile = File(...),
) -> KpEventNametagBackground:
    return await export_service.upload_nametag_background(
        event_id=event_id,
        filename=file.filename or "nametag-background",
        upload=file,
        content_length=upload_size(request, file),
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
    columns: int | None = Query(default=None, ge=1, le=2),
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
    columns: int | None = Query(default=None, ge=1, le=2),
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


NAMETAG_PREVIEW_RATE_LIMIT = user_rate_limit(
    "nametag_preview",
    get_settings().BOOKLET_PAGE_RATE_LIMIT_MAX_REQUESTS,
    get_settings().BOOKLET_PAGE_RATE_LIMIT_WINDOW_SECONDS,
)


@router.get(
    "/events/{event_id}/exports/nametags/preview",
    operation_id="previewEventNametag",
    response_model=NametagPreviewResponse,
    dependencies=[NAMETAG_PREVIEW_RATE_LIMIT],
)
async def preview_event_nametag(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> NametagPreviewResult:
    return await export_service.preview_event_nametag(event_id)


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
    "/events/{event_id}/exports/companies/download",
    operation_id="downloadEventCompaniesXlsx",
)
async def download_event_companies_xlsx(
    export_service: ExportServiceDep,
    event_id: UUID,
    language: ExportLanguage = ExportLanguage.DE,
) -> Response:
    export = await export_service.export_company_workbook(event_id, language)
    return _xlsx_download(export.content, export.filename)


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
    "/events/{event_id}/exports/registration-exceptions/download",
    operation_id="downloadEventRegistrationExceptionsCsv",
)
async def download_event_registration_exceptions_csv(
    export_service: ExportServiceDep,
    event_id: UUID,
) -> Response:
    export = await export_service.export_registration_exceptions_csv(event_id)
    return _csv_download(export.content, export.filename)
