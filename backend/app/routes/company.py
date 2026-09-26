from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, File, Query, Request, UploadFile

from app.core.config import get_settings
from app.core.deps import (
    BookletServiceDep,
    CompanyServiceDep,
    CsrfDep,
    InviteServiceDep,
)
from app.core.rate_limit import user_rate_limit
from app.core.uploads import upload_size
from app.models.company import Company
from app.models.user import User
from app.schemas.company import (
    AddCompanyMemberRequest,
    BookletPageResponse,
    BookletPageResult,
    CompanyListResponse,
    CompanyListResult,
    CompanyPageResponse,
    CompanyPageResult,
    CompanyProfileResponse,
    CompanyProfileResult,
    CompanyResponse,
    CompanyWithUsersResponse,
    CompanyWithUsersResult,
    CreateInviteRequest,
    InviteInfoResponse,
    InviteInfoResult,
    MyCompanyResponse,
    MyCompanyResult,
    SetupCompanyRequest,
    UpdateCompanyProfileRequest,
    UpdateCompanyRequest,
)
from app.schemas.user import StaffUserResponse, UserResponse

MAX_PAGE_SIZE = 100
BOOKLET_PAGE_RATE_LIMIT = user_rate_limit(
    "booklet_page",
    get_settings().BOOKLET_PAGE_RATE_LIMIT_MAX_REQUESTS,
    get_settings().BOOKLET_PAGE_RATE_LIMIT_WINDOW_SECONDS,
)

public_router = APIRouter(prefix="/company", tags=["company"])
router = APIRouter(prefix="/company", tags=["company"], dependencies=[CsrfDep])
companies_router = APIRouter(
    prefix="/companies", tags=["company"], dependencies=[CsrfDep]
)


@router.post("/setup", operation_id="setupCompany", response_model=CompanyResponse)
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


@router.get("/me", operation_id="getMyCompany", response_model=MyCompanyResponse)
async def get_my_company(company_service: CompanyServiceDep) -> MyCompanyResult:
    return await company_service.get_my_company()


@router.get(
    "/me/profile",
    operation_id="getMyCompanyProfile",
    response_model=CompanyProfileResponse,
)
async def get_my_company_profile(
    company_service: CompanyServiceDep,
) -> CompanyProfileResult:
    return await company_service.get_my_profile()


@router.put(
    "/me/profile",
    operation_id="updateMyCompanyProfile",
    response_model=CompanyProfileResponse,
)
async def update_my_company_profile(
    company_service: CompanyServiceDep,
    request: UpdateCompanyProfileRequest,
) -> CompanyProfileResult:
    return await company_service.update_my_profile(request)


@router.post(
    "/me/profile/logo",
    operation_id="uploadMyCompanyProfileLogo",
    response_model=CompanyProfileResponse,
)
async def upload_my_company_profile_logo(
    company_service: CompanyServiceDep,
    request: Request,
    file: UploadFile = File(...),
) -> CompanyProfileResult:
    return await company_service.upload_my_profile_logo(
        filename=file.filename or "company-logo",
        upload=file,
        content_length=upload_size(request, file),
        content_type=file.content_type,
    )


@router.delete(
    "/me/profile/logo",
    operation_id="deleteMyCompanyProfileLogo",
    response_model=CompanyProfileResponse,
)
async def delete_my_company_profile_logo(
    company_service: CompanyServiceDep,
) -> CompanyProfileResult:
    return await company_service.delete_my_profile_logo()


@router.post(
    "/me/profile/booklet-page",
    operation_id="previewMyCompanyBookletPage",
    response_model=BookletPageResponse,
    dependencies=[BOOKLET_PAGE_RATE_LIMIT],
)
async def preview_my_company_booklet_page(
    booklet_service: BookletServiceDep,
    request: UpdateCompanyProfileRequest,
) -> BookletPageResult:
    return await booklet_service.preview_my_company_page(request)


@router.get(
    "/{company_id}/profile",
    operation_id="getCompanyProfile",
    response_model=CompanyProfileResponse,
)
async def get_company_profile(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> CompanyProfileResult:
    return await company_service.get_company_profile(company_id)


@router.put(
    "/{company_id}/profile",
    operation_id="updateCompanyProfile",
    response_model=CompanyProfileResponse,
)
async def update_company_profile(
    company_service: CompanyServiceDep,
    company_id: UUID,
    request: UpdateCompanyProfileRequest,
) -> CompanyProfileResult:
    return await company_service.update_company_profile(company_id, request)


@router.post(
    "/{company_id}/profile/booklet-page",
    operation_id="previewCompanyBookletPage",
    response_model=BookletPageResponse,
    dependencies=[BOOKLET_PAGE_RATE_LIMIT],
)
async def preview_company_booklet_page(
    booklet_service: BookletServiceDep,
    company_id: UUID,
    request: UpdateCompanyProfileRequest,
) -> BookletPageResult:
    return await booklet_service.preview_company_page(company_id, request)


@router.post(
    "/{company_id}/profile/logo",
    operation_id="uploadCompanyProfileLogo",
    response_model=CompanyProfileResponse,
)
async def upload_company_profile_logo(
    company_service: CompanyServiceDep,
    company_id: UUID,
    request: Request,
    file: UploadFile = File(...),
) -> CompanyProfileResult:
    return await company_service.upload_company_profile_logo(
        company_id,
        filename=file.filename or "company-logo",
        upload=file,
        content_length=upload_size(request, file),
        content_type=file.content_type,
    )


@router.delete(
    "/{company_id}/profile/logo",
    operation_id="deleteCompanyProfileLogo",
    response_model=CompanyProfileResponse,
)
async def delete_company_profile_logo(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> CompanyProfileResult:
    return await company_service.delete_company_profile_logo(company_id)


@router.post(
    "/invite",
    operation_id="createCompanyInvite",
    dependencies=[user_rate_limit("company_invite")],
)
async def create_company_invite(
    company_service: CompanyServiceDep,
    request: CreateInviteRequest,
) -> None:
    await company_service.create_invite(request.email)


@public_router.get(
    "/invite/{token}",
    operation_id="getCompanyInviteInfo",
    response_model=InviteInfoResponse,
)
async def get_company_invite_info(
    invite_service: InviteServiceDep,
    token: str,
) -> InviteInfoResult:
    return await invite_service.get_invite_info(token)


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
    response_model=list[StaffUserResponse],
)
async def get_company_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> Sequence[User]:
    return await company_service.get_company_users(company_id)


@router.get(
    "/{company_id}/with-users",
    operation_id="getCompanyWithUsers",
    response_model=CompanyWithUsersResponse,
)
async def get_company_with_users(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> CompanyWithUsersResult:
    return await company_service.get_company_with_users(company_id)


@router.get(
    "/management/companies",
    operation_id="listCompanies",
    response_model=list[CompanyListResponse],
)
async def list_companies(
    company_service: CompanyServiceDep,
) -> Sequence[CompanyListResult]:
    return await company_service.get_companies()


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


@router.patch("/me", operation_id="updateMyCompany", response_model=CompanyResponse)
async def update_my_company(
    company_service: CompanyServiceDep,
    request: UpdateCompanyRequest,
) -> Company:
    return await company_service.update_company_name(request.name)


@companies_router.get(
    "",
    operation_id="searchCompanies",
    response_model=CompanyPageResponse,
)
async def search_companies(
    company_service: CompanyServiceDep,
    query: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
) -> CompanyPageResult:
    return await company_service.search_companies(query, page, page_size)


@companies_router.patch(
    "/{company_id}",
    operation_id="updateCompany",
    response_model=CompanyResponse,
)
async def update_company(
    company_service: CompanyServiceDep,
    company_id: UUID,
    request: UpdateCompanyRequest,
) -> Company:
    return await company_service.update_company(company_id, request.name)


@companies_router.post(
    "/{company_id}/members",
    operation_id="addCompanyMember",
    response_model=UserResponse,
)
async def add_company_member(
    company_service: CompanyServiceDep,
    company_id: UUID,
    request: AddCompanyMemberRequest,
) -> User:
    return await company_service.add_company_user(company_id, request.user_id)


@companies_router.post(
    "/{company_id}/members/acknowledge",
    operation_id="acknowledgeCompanyNewMembers",
    response_model=list[StaffUserResponse],
)
async def acknowledge_company_new_members(
    company_service: CompanyServiceDep,
    company_id: UUID,
) -> Sequence[User]:
    return await company_service.acknowledge_new_members(company_id)


@companies_router.delete(
    "/{company_id}/members/{user_id}",
    operation_id="removeCompanyUser",
)
async def remove_company_user(
    company_service: CompanyServiceDep,
    company_id: UUID,
    user_id: UUID,
) -> None:
    await company_service.remove_company_user(company_id, user_id)
