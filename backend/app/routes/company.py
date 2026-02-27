from uuid import UUID
from fastapi import APIRouter, status
from app.core.deps import AuthServiceDep, CompanyServiceDep, CsrfDep, UserServiceDep
from app.models.company import Company
from app.models.user import User
from app.schemas.company import (
    CompanyWithUsersResponse,
    CreateCompanyRequest,
    UpdateCompanyRequest,
)

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


@router.get("/management", operation_id="listCompaniesWithUsers")
async def list_companies_with_users(
    company_service: CompanyServiceDep,
) -> list[CompanyWithUsersResponse]:
    return await company_service.get_companies_with_users()


@router.delete(
    "/{company_id}/delete-with-users",
    operation_id="deleteCompanyWithUsers",
)
async def delete_company_with_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
):
    await company_service.delete_company_with_users(company_id)


@router.delete(
    "/{company_id}/delete-keep-users",
    operation_id="deleteCompanyKeepUsers",
)
async def delete_company_keep_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
):
    await company_service.delete_company_keep_users(company_id)


@router.delete(
    "/{company_id}/users/{user_id}",
    operation_id="removeCompanyUser",
)
async def remove_company_user(
    user_service: UserServiceDep,
    company_id: UUID,
    user_id: UUID,
):
    await user_service.remove_company_user(company_id, user_id)


@router.patch("/me", operation_id="updateMyCompany")
async def update_my_company(
    company_service: CompanyServiceDep,
    request: UpdateCompanyRequest,
) -> Company:
    return await company_service.update_company_name(request.name)
