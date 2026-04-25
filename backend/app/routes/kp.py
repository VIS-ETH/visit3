from fastapi import APIRouter

from app.core.deps import CsrfDep, KpServiceDep
from app.models.kp_event import KpEvent
from app.schemas.kp import CreateKpRequest, KpResponse

router = APIRouter(prefix="/kp", tags=["kp"], dependencies=[CsrfDep])


def _serialize_kp(event: KpEvent) -> KpResponse:
    return KpResponse(
        id=event.id,
        name=event.name,
        registration_open=event.registration_open,
        registration_end=event.registration_end,
        finalization_deadline=event.finalization_deadline,
        event_date=event.event_date,
    )


@router.get("/list", operation_id="listKps")
async def list_kps(kp_service: KpServiceDep) -> list[KpResponse]:
    return [_serialize_kp(event) for event in await kp_service.list_kps()]


@router.get("/latest", operation_id="getLatestKp")
async def get_latest_kp(kp_service: KpServiceDep) -> KpResponse | None:
    event = await kp_service.get_latest_kp()
    return _serialize_kp(event) if event is not None else None


@router.get("/name/{name}", operation_id="getKpByName")
async def get_kp_by_name(kp_service: KpServiceDep, name: str) -> KpResponse | None:
    event = await kp_service.get_event_by_name(name)
    return _serialize_kp(event) if event is not None else None


@router.post("/create", operation_id="createKp")
async def create_kp(kp_service: KpServiceDep, request: CreateKpRequest) -> KpResponse:
    event = await kp_service.create_kp(
        name=request.name,
        registration_open=request.registration_open,
        registration_end=request.registration_end,
        finalization_deadline=request.finalization_deadline,
        event_date=request.event_date,
    )
    return _serialize_kp(event)
