from uuid import UUID
from fastapi import APIRouter
from app.core.deps import AuthServiceDep, CompanyServiceDep, CsrfDep
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CreateCompanyRequest

router = APIRouter(prefix="/company", tags=["company"], dependencies=[CsrfDep])


@router.get("/list", operation_id="listCompanies")
async def list_companies(auth_service: AuthServiceDep) -> list[Company]:
    return await auth_service.get_companies()


@router.post("/create", operation_id="createCompany")
async def create_company(
    auth_service: AuthServiceDep,
    request: CreateCompanyRequest,
) -> Company:
    return await auth_service.create_company(request.name)


@router.get("/{company_id}/users", operation_id="getCompanyUsers")
async def get_company_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> list[User]:
    return await company_service.get_company_users(company_id)
