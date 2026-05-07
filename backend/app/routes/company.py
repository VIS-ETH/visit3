from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CompanyServiceDep, CsrfDep
from app.models.company import Company
from app.models.user import User
from app.schemas.company import (
    CompanyWithUsersResponse,
    CompanyWithUsersResult,
    CreateInviteRequest,
    InviteInfoResponse,
    InviteInfoResult,
    KpCompanyProfileResponse,
    KpCompanyProfileResult,
    SetupCompanyRequest,
    UpdateCompanyRequest,
    UpdateKpCompanyProfileRequest,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/company", tags=["company"], dependencies=[CsrfDep])


@router.post("/setup", operation_id="setupCompany", response_model=Company)
async def setup_company(
    company_service: CompanyServiceDep,
    request: SetupCompanyRequest,
) -> Company:
    return await company_service.setup_company(request.name)


@router.get(
    "/me/members",
    operation_id="getMyCompanyMembers",
    response_model=list[UserResponse],
)
async def get_my_company_members(
    company_service: CompanyServiceDep,
) -> Sequence[User]:
    return await company_service.get_my_members()


@router.get(
    "/me/kp-profile",
    operation_id="getMyKpCompanyProfile",
    response_model=KpCompanyProfileResponse | None,
)
async def get_my_kp_company_profile(
    company_service: CompanyServiceDep,
) -> KpCompanyProfileResult | None:
    return await company_service.get_my_kp_profile()


@router.put(
    "/me/kp-profile",
    operation_id="updateMyKpCompanyProfile",
    response_model=KpCompanyProfileResponse,
)
async def update_my_kp_company_profile(
    company_service: CompanyServiceDep,
    request: UpdateKpCompanyProfileRequest,
) -> KpCompanyProfileResult:
    return await company_service.update_my_kp_profile(
        invoice_address=request.invoice_address,
        shipping_address=request.shipping_address,
        contact_email=request.contact_email,
        kp_contact_user_id=request.kp_contact_user_id,
    )


@router.post("/invite", operation_id="createCompanyInvite")
async def create_company_invite(
    company_service: CompanyServiceDep,
    request: CreateInviteRequest,
) -> None:
    await company_service.create_invite(request.email)


@router.get(
    "/invite/{token}",
    operation_id="getCompanyInviteInfo",
    response_model=InviteInfoResponse,
)
async def get_company_invite_info(
    company_service: CompanyServiceDep,
    token: str,
) -> InviteInfoResult:
    return await company_service.get_invite_info(token)


@router.post(
    "/invite/{token}/accept",
    operation_id="acceptCompanyInvite",
    response_model=UserResponse,
)
async def accept_company_invite(
    company_service: CompanyServiceDep,
    token: str,
) -> User:
    return await company_service.accept_invite(token)


@router.get(
    "/{company_id}/users",
    operation_id="getCompanyUsers",
    response_model=list[UserResponse],
)
async def get_company_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> Sequence[User]:
    return await company_service.get_company_users(company_id)


@router.get(
    "/management",
    operation_id="listCompaniesWithUsers",
    response_model=list[CompanyWithUsersResponse],
)
async def list_companies_with_users(
    company_service: CompanyServiceDep,
) -> Sequence[CompanyWithUsersResult]:
    return await company_service.get_companies_with_users()


@router.delete(
    "/{company_id}/delete-with-users",
    operation_id="deleteCompanyWithUsers",
)
async def delete_company_with_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> None:
    await company_service.delete_company_with_users(company_id)


@router.delete(
    "/{company_id}/delete-keep-users",
    operation_id="deleteCompanyKeepUsers",
)
async def delete_company_keep_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> None:
    await company_service.delete_company_keep_users(company_id)


@router.delete(
    "/{company_id}/users/{user_id}",
    operation_id="removeCompanyUser",
)
async def remove_company_user(
    company_service: CompanyServiceDep,
    company_id: UUID,
    user_id: UUID,
) -> None:
    await company_service.remove_company_user(company_id, user_id)


@router.patch("/me", operation_id="updateMyCompany", response_model=Company)
async def update_my_company(
    company_service: CompanyServiceDep,
    request: UpdateCompanyRequest,
) -> Company:
    return await company_service.update_company_name(request.name)
