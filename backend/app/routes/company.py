from uuid import UUID

from fastapi import APIRouter

from app.core.decorators import require_admin, require_confirmed_company, require_staff
from app.core.deps import CompanyServiceDep, CsrfDep, UserServiceDep
from app.models.company import Company
from app.schemas.company import (
    CompanyWithUsersResponse,
    CreateInviteRequest,
    InviteInfoResponse,
    KpCompanyProfileResponse,
    SetupCompanyRequest,
    UpdateCompanyRequest,
    UpdateKpCompanyProfileRequest,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/company", tags=["company"], dependencies=[CsrfDep])


@router.post("/setup", operation_id="setupCompany")
async def setup_company(
    company_service: CompanyServiceDep,
    request: SetupCompanyRequest,
) -> Company:
    return await company_service.setup_company(request.name)


@router.get(
    "/me/members",
    operation_id="getMyCompanyMembers",
)
@require_confirmed_company
async def get_my_company_members(
    company_service: CompanyServiceDep,
) -> list[UserResponse]:
    return [
        UserResponse.model_validate(user, from_attributes=True)
        for user in await company_service.get_my_members()
    ]


@router.get("/me/kp-profile", operation_id="getMyKpCompanyProfile")
@require_confirmed_company
async def get_my_kp_company_profile(
    company_service: CompanyServiceDep,
) -> KpCompanyProfileResponse | None:
    return await company_service.get_my_kp_profile()


@router.put("/me/kp-profile", operation_id="updateMyKpCompanyProfile")
@require_confirmed_company
async def update_my_kp_company_profile(
    company_service: CompanyServiceDep,
    request: UpdateKpCompanyProfileRequest,
) -> KpCompanyProfileResponse:
    return await company_service.update_my_kp_profile(
        invoice_address=request.invoice_address,
        shipping_address=request.shipping_address,
        contact_email=request.contact_email,
        kp_contact_user_id=request.kp_contact_user_id,
    )


@router.post("/invite", operation_id="createCompanyInvite")
@require_confirmed_company
async def create_company_invite(
    company_service: CompanyServiceDep,
    request: CreateInviteRequest,
):
    await company_service.create_invite(request.email)


@router.get(
    "/invite/{token}",
    operation_id="getCompanyInviteInfo",
)
async def get_company_invite_info(
    company_service: CompanyServiceDep,
    token: str,
) -> InviteInfoResponse:
    return await company_service.get_invite_info(token)


@router.post(
    "/invite/{token}/accept",
    operation_id="acceptCompanyInvite",
)
@require_confirmed_company
async def accept_company_invite(
    company_service: CompanyServiceDep,
    token: str,
) -> UserResponse:
    return UserResponse.model_validate(
        await company_service.accept_invite(token),
        from_attributes=True,
    )


@router.get(
    "/{company_id}/users",
    operation_id="getCompanyUsers",
)
@require_staff
async def get_company_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> list[UserResponse]:
    return [
        UserResponse.model_validate(user, from_attributes=True)
        for user in await company_service.get_company_users(company_id)
    ]


@router.get("/management", operation_id="listCompaniesWithUsers")
@require_staff
async def list_companies_with_users(
    company_service: CompanyServiceDep,
) -> list[CompanyWithUsersResponse]:
    return await company_service.get_companies_with_users()


@router.delete(
    "/{company_id}/delete-with-users",
    operation_id="deleteCompanyWithUsers",
)
@require_admin
async def delete_company_with_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
):
    await company_service.delete_company_with_users(company_id)


@router.delete(
    "/{company_id}/delete-keep-users",
    operation_id="deleteCompanyKeepUsers",
)
@require_admin
async def delete_company_keep_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
):
    await company_service.delete_company_keep_users(company_id)


@router.delete(
    "/{company_id}/users/{user_id}",
    operation_id="removeCompanyUser",
)
@require_admin
async def remove_company_user(
    user_service: UserServiceDep,
    company_id: UUID,
    user_id: UUID,
):
    await user_service.remove_company_user(company_id, user_id)


@router.patch("/me", operation_id="updateMyCompany")
@require_confirmed_company
async def update_my_company(
    company_service: CompanyServiceDep,
    request: UpdateCompanyRequest,
) -> Company:
    return await company_service.update_company_name(request.name)
