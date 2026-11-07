from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import EventBannerServiceDep, KpServiceDep
from app.models.kp_event import KpEvent
from app.schemas.kp import (
    CloneKpRequest,
    CreateKpRequest,
    KpLatestResponse,
    KpLatestResult,
    KpResponse,
    KpStaffResponse,
    UpdateKpRequest,
)

router = APIRouter()


@router.get("/list", operation_id="listKps", response_model=list[KpResponse])
async def list_kps(kp_service: KpServiceDep) -> Sequence[KpEvent]:
    return await kp_service.list_kps()


@router.get(
    "/latest", operation_id="getLatestKp", response_model=KpLatestResponse | None
)
async def get_latest_kp(
    event_banner_service: EventBannerServiceDep,
) -> KpLatestResult | None:
    return await event_banner_service.latest_event()


@router.get("/events/{event_id}", operation_id="getKpById", response_model=KpResponse)
async def get_kp_by_id(kp_service: KpServiceDep, event_id: UUID) -> KpEvent:
    return await kp_service.get_event_by_id(event_id)


@router.get(
    "/events/{event_id}/settings",
    operation_id="getKpSettings",
    response_model=KpStaffResponse,
)
async def get_kp_settings(kp_service: KpServiceDep, event_id: UUID) -> KpEvent:
    return await kp_service.get_event_settings(event_id)


@router.post("/create", operation_id="createKp", response_model=KpStaffResponse)
async def create_kp(kp_service: KpServiceDep, request: CreateKpRequest) -> KpEvent:
    return await kp_service.create_kp(request)


@router.patch(
    "/events/{event_id}", operation_id="updateKp", response_model=KpStaffResponse
)
async def update_kp(
    kp_service: KpServiceDep, event_id: UUID, request: UpdateKpRequest
) -> KpEvent:
    return await kp_service.update_kp(event_id, request)


@router.post(
    "/events/{event_id}/clone",
    operation_id="cloneKp",
    response_model=KpStaffResponse,
)
async def clone_kp(
    kp_service: KpServiceDep, event_id: UUID, request: CloneKpRequest
) -> KpEvent:
    return await kp_service.clone_kp(event_id, request)
