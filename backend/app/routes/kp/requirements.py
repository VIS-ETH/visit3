from uuid import UUID

from fastapi import APIRouter, File, Request, UploadFile

from app.core.deps import KpServiceDep
from app.core.uploads import upload_size
from app.models.kp_event import KpEventBookingServiceFileLink
from app.schemas.kp import (
    BookingRequirementFileMapResponse,
    RequirementFileDownloadResponse,
    RequirementFileResponse,
    RequirementTextRequest,
    RequirementTextResponse,
)

router = APIRouter()


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
    request: Request,
    booking_service_id: UUID,
    requirement_id: UUID,
    file: UploadFile = File(...),
) -> KpEventBookingServiceFileLink:
    return await kp_service.upload_booking_requirement_file(
        booking_service_id=booking_service_id,
        requirement_id=requirement_id,
        filename=file.filename or "upload.bin",
        upload=file,
        content_length=upload_size(request, file),
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
    await kp_service.delete_booking_requirement_answer(
        booking_service_id, requirement_id
    )


@router.delete(
    "/booking-services/{booking_service_id}/requirements/{requirement_id}/text",
    operation_id="deleteBookingRequirementText",
)
async def delete_booking_requirement_text(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
) -> None:
    await kp_service.delete_booking_requirement_answer(
        booking_service_id, requirement_id
    )


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
    "/booking-services/{booking_service_id}/requirements/{requirement_id}/text",
    operation_id="getBookingRequirementText",
    response_model=RequirementTextResponse | None,
)
async def get_booking_requirement_text(
    kp_service: KpServiceDep,
    booking_service_id: UUID,
    requirement_id: UUID,
) -> RequirementTextResponse | None:
    return await kp_service.get_booking_requirement_text(
        booking_service_id, requirement_id
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
