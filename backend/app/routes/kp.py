from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CsrfDep, KpServiceDep
from app.models.company import Company
from app.models.kp_event import KpEvent
from app.schemas.kp import CreateKpRequest

router = APIRouter(prefix="/kp", tags=["kp"], dependencies=[CsrfDep])


@router.get("/list", operation_id="listKps")
async def list_kps(kp_service: KpServiceDep) -> list[KpEvent]:
    return await kp_service.list_kps()


@router.get("/latest", operation_id="getLatestKp")
async def get_latest_kp(kp_service: KpServiceDep) -> KpEvent | None:
    return await kp_service.get_latest_kp()


@router.get("/year/{year}", operation_id="getKpByYear")
async def get_kp_by_year(kp_service: KpServiceDep, year: int) -> KpEvent | None:
    return await kp_service.get_event_by_year(year)


@router.post("/create", operation_id="createKp")
async def create_kp(kp_service: KpServiceDep, request: CreateKpRequest) -> KpEvent:
    return await kp_service.create_kp(
        year=request.year,
        registration_open=request.registration_open,
        registration_end=request.registration_end,
        event_date=request.event_date,
    )


@router.post("/{event_id}/register", operation_id="registerCompanyForKp")
async def register_company_for_kp(kp_service: KpServiceDep, event_id: UUID):
    await kp_service.register_company_for_kp(event_id)


@router.delete("/{event_id}/register", operation_id="deregisterCompanyFromKp")
async def deregister_company_from_kp(kp_service: KpServiceDep, event_id: UUID):
    await kp_service.deregister_company_from_kp(event_id)


@router.get("/{event_id}/companies", operation_id="getCompaniesForKp")
async def get_companies_for_kp(
    kp_service: KpServiceDep, event_id: UUID
) -> list[Company]:
    return await kp_service.get_companies_for_kp(event_id)
