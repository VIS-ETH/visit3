from fastapi import APIRouter

from app.core.deps import CsrfDep, KpServiceDep
from app.models.kp_event import KpEvent
from app.schemas.kp import CreateKpRequest

router = APIRouter(prefix="/kp", tags=["kp"], dependencies=[CsrfDep])


@router.get("/list", operation_id="listKps")
async def list_kps(kp_service: KpServiceDep) -> list[KpEvent]:
    return await kp_service.list_kps()


@router.get("/latest", operation_id="getLatestKp")
async def get_latest_kp(kp_service: KpServiceDep) -> KpEvent | None:
    return await kp_service.get_latest_kp()


@router.get("/name/{name}", operation_id="getKpByName")
async def get_kp_by_name(kp_service: KpServiceDep, name: str) -> KpEvent | None:
    return await kp_service.get_event_by_name(name)


@router.post("/create", operation_id="createKp")
async def create_kp(kp_service: KpServiceDep, request: CreateKpRequest) -> KpEvent:
    return await kp_service.create_kp(
        name=request.name,
        registration_open=request.registration_open,
        registration_end=request.registration_end,
        finalization_deadline=request.finalization_deadline,
        event_date=request.event_date,
    )
