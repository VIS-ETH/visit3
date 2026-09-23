from uuid import UUID

from fastapi import APIRouter, File, Request, UploadFile

from app.core.deps import CsrfDep, VenueServiceDep
from app.core.uploads import upload_size
from app.schemas.venue import (
    CreateVenueLayoutRequest,
    ReplaceVenueBoothsRequest,
    ReplaceVenueZoneShapesRequest,
    UpdateVenueLayoutRequest,
    VenueLayoutResponse,
    VenueLayoutResult,
    VenueMapResponse,
    VenueMapResult,
)

router = APIRouter(prefix="/kp", tags=["kp"], dependencies=[CsrfDep])


@router.get(
    "/events/{event_id}/venue-layouts",
    operation_id="listVenueLayouts",
    response_model=list[VenueLayoutResponse],
)
async def list_venue_layouts(
    venue_service: VenueServiceDep, event_id: UUID
) -> list[VenueLayoutResult]:
    return await venue_service.list_layouts(event_id)


@router.post(
    "/events/{event_id}/venue-layouts",
    operation_id="createVenueLayout",
    response_model=VenueLayoutResponse,
)
async def create_venue_layout(
    venue_service: VenueServiceDep,
    event_id: UUID,
    request: CreateVenueLayoutRequest,
) -> VenueLayoutResult:
    return await venue_service.create_layout(event_id, request)


@router.patch(
    "/venue-layouts/{layout_id}",
    operation_id="updateVenueLayout",
    response_model=VenueLayoutResponse,
)
async def update_venue_layout(
    venue_service: VenueServiceDep,
    layout_id: UUID,
    request: UpdateVenueLayoutRequest,
) -> VenueLayoutResult:
    return await venue_service.update_layout(layout_id, request)


@router.delete("/venue-layouts/{layout_id}", operation_id="deleteVenueLayout")
async def delete_venue_layout(venue_service: VenueServiceDep, layout_id: UUID) -> None:
    await venue_service.delete_layout(layout_id)


@router.put(
    "/venue-layouts/{layout_id}/background",
    operation_id="uploadVenueLayoutBackground",
    response_model=VenueLayoutResponse,
)
async def upload_venue_layout_background(
    venue_service: VenueServiceDep,
    request: Request,
    layout_id: UUID,
    file: UploadFile = File(...),
) -> VenueLayoutResult:
    return await venue_service.upload_background(
        layout_id=layout_id,
        filename=file.filename or "venue-background",
        upload=file,
        content_length=upload_size(request, file),
        content_type=file.content_type,
    )


@router.delete(
    "/venue-layouts/{layout_id}/background",
    operation_id="deleteVenueLayoutBackground",
    response_model=VenueLayoutResponse,
)
async def delete_venue_layout_background(
    venue_service: VenueServiceDep, layout_id: UUID
) -> VenueLayoutResult:
    return await venue_service.delete_background(layout_id)


@router.put(
    "/venue-layouts/{layout_id}/shapes",
    operation_id="replaceVenueZoneShapes",
    response_model=VenueLayoutResponse,
)
async def replace_venue_zone_shapes(
    venue_service: VenueServiceDep,
    layout_id: UUID,
    request: ReplaceVenueZoneShapesRequest,
) -> VenueLayoutResult:
    return await venue_service.replace_zone_shapes(layout_id, request.shapes)


@router.put(
    "/venue-layouts/{layout_id}/booths",
    operation_id="replaceVenueBooths",
    response_model=VenueLayoutResponse,
)
async def replace_venue_booths(
    venue_service: VenueServiceDep,
    layout_id: UUID,
    request: ReplaceVenueBoothsRequest,
) -> VenueLayoutResult:
    return await venue_service.replace_booths(layout_id, request.booths)


@router.get(
    "/events/{event_id}/venue",
    operation_id="getEventVenue",
    response_model=VenueMapResponse,
)
async def get_event_venue(
    venue_service: VenueServiceDep, event_id: UUID
) -> VenueMapResult:
    return await venue_service.get_event_venue(event_id)
