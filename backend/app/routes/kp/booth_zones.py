from uuid import UUID

from fastapi import APIRouter, File, Request, UploadFile

from app.core.deps import KpServiceDep
from app.core.uploads import upload_size
from app.schemas.kp import (
    CreateBoothZoneRequest,
    ReorderBoothZonesRequest,
    StaffBoothZoneResponse,
    UpdateBoothZoneRequest,
)

router = APIRouter()


@router.get(
    "/events/{event_id}/booth-zones",
    operation_id="listBoothZones",
    response_model=list[StaffBoothZoneResponse],
)
async def list_booth_zones(
    kp_service: KpServiceDep, event_id: UUID
) -> list[StaffBoothZoneResponse]:
    return await kp_service.list_booth_zones(event_id)


@router.post(
    "/events/{event_id}/booth-zones",
    operation_id="createBoothZone",
    response_model=StaffBoothZoneResponse,
)
async def create_booth_zone(
    kp_service: KpServiceDep, event_id: UUID, request: CreateBoothZoneRequest
) -> StaffBoothZoneResponse:
    return await kp_service.create_booth_zone(event_id, request)


@router.put(
    "/events/{event_id}/booth-zones/order",
    operation_id="reorderBoothZones",
    response_model=list[StaffBoothZoneResponse],
)
async def reorder_booth_zones(
    kp_service: KpServiceDep, event_id: UUID, request: ReorderBoothZonesRequest
) -> list[StaffBoothZoneResponse]:
    return await kp_service.reorder_booth_zones(event_id, request.booth_zone_ids)


@router.patch(
    "/booth-zones/{booth_zone_id}",
    operation_id="updateBoothZone",
    response_model=StaffBoothZoneResponse,
)
async def update_booth_zone(
    kp_service: KpServiceDep,
    booth_zone_id: UUID,
    request: UpdateBoothZoneRequest,
) -> StaffBoothZoneResponse:
    return await kp_service.update_booth_zone(booth_zone_id, request)


@router.delete("/booth-zones/{booth_zone_id}", operation_id="deleteBoothZone")
async def delete_booth_zone(kp_service: KpServiceDep, booth_zone_id: UUID) -> None:
    await kp_service.delete_booth_zone(booth_zone_id)


@router.put(
    "/booth-zones/{booth_zone_id}/layout-file",
    operation_id="uploadBoothZoneLayoutFile",
    response_model=StaffBoothZoneResponse,
)
async def upload_booth_zone_layout_file(
    kp_service: KpServiceDep,
    request: Request,
    booth_zone_id: UUID,
    file: UploadFile = File(...),
) -> StaffBoothZoneResponse:
    return await kp_service.upload_booth_zone_layout_file(
        booth_zone_id=booth_zone_id,
        filename=file.filename or "booth-zone-layout",
        upload=file,
        content_length=upload_size(request, file),
        content_type=file.content_type,
    )


@router.delete(
    "/booth-zones/{booth_zone_id}/layout-file",
    operation_id="deleteBoothZoneLayoutFile",
    response_model=StaffBoothZoneResponse,
)
async def delete_booth_zone_layout_file(
    kp_service: KpServiceDep,
    booth_zone_id: UUID,
) -> StaffBoothZoneResponse:
    return await kp_service.delete_booth_zone_layout_file(booth_zone_id)
