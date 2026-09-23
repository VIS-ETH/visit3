import logging
from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Query, Response

from app.core.deps import AuthServiceDep, CsrfDep, CurrentUserDep, UserServiceDep
from app.core.rate_limit import user_rate_limit
from app.models.user import User
from app.schemas.user import (
    CompanyUserResponse,
    UpdateCompanyUserRequest,
    UpdateUserProfileRequest,
    UserFilter,
    UserPageResponse,
    UserPageResult,
    UserResponse,
)

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 100

public_router = APIRouter(prefix="/user", tags=["user"])
router = APIRouter(prefix="/user", tags=["user"], dependencies=[CsrfDep])
users_router = APIRouter(prefix="/users", tags=["user"], dependencies=[CsrfDep])


@router.get("/me", operation_id="getCurrentUser", response_model=UserResponse)
async def get_current_user(user_service: UserServiceDep) -> User:
    return await user_service.get_current_user()


@router.get(
    "/profile",
    operation_id="getUserProfile",
    response_model=CompanyUserResponse,
)
async def get_user_profile(user_service: UserServiceDep) -> User:
    return await user_service.get_current_user_profile()


@router.patch(
    "/me",
    operation_id="updateUserProfile",
    response_model=CompanyUserResponse,
)
async def update_user_profile(
    user_service: UserServiceDep, request: UpdateUserProfileRequest
) -> User:
    return await user_service.update_current_user_profile(request)


@router.get(
    "/companies",
    operation_id="getAllCompanyUsers",
    response_model=list[CompanyUserResponse],
)
async def get_all_company_users(
    user_service: UserServiceDep,
) -> Sequence[User]:
    return await user_service.get_company_users()


@router.get(
    "/admins",
    operation_id="getAllAdmins",
    response_model=list[UserResponse],
)
async def get_all_admins(user_service: UserServiceDep) -> Sequence[User]:
    return await user_service.get_admins()


@router.get(
    "/staff",
    operation_id="getAllStaff",
    response_model=list[UserResponse],
)
async def get_all_staff(user_service: UserServiceDep) -> Sequence[User]:
    return await user_service.get_staff()


@router.post(
    "/send-confirmation-email",
    operation_id="sendConfirmationMail",
    dependencies=[user_rate_limit("send_confirmation_email")],
)
async def send_confirmation_mail(
    auth_service: AuthServiceDep,
    current_user: CurrentUserDep,
) -> None:
    return await auth_service.send_confirm_email(current_user)


@public_router.post("/confirm-email/{token}", operation_id="confirmEmail")
async def confirm_email(auth_service: AuthServiceDep, token: str) -> bool:
    return await auth_service.confirm_email(token)


@public_router.get("/confirm-email/{token}", operation_id="validateConfirmEmailToken")
async def validate_confirm_email_token(
    auth_service: AuthServiceDep, token: str
) -> bool:
    return await auth_service.validate_confirm_email_token(token)


@router.get(
    "/unconfirmed",
    operation_id="getUnconfirmedUsers",
    response_model=list[CompanyUserResponse],
)
async def get_unconfirmed_users(
    user_service: UserServiceDep,
) -> Sequence[User]:
    return await user_service.get_unconfirmed_users()


@users_router.get(
    "",
    operation_id="listUsers",
    response_model=UserPageResponse,
)
async def list_users(
    user_service: UserServiceDep,
    query: str | None = None,
    filter: UserFilter = UserFilter.ALL,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
) -> UserPageResult:
    return await user_service.list_users(query, filter, page, page_size)


@users_router.get(
    "/{user_id}",
    operation_id="getUser",
    response_model=UserResponse,
)
async def get_user(user_service: UserServiceDep, user_id: UUID) -> User:
    return await user_service.get_user(user_id)


@users_router.post(
    "/{user_id}/confirm",
    operation_id="confirmUser",
    response_model=UserResponse,
)
async def confirm_user(user_service: UserServiceDep, user_id: UUID) -> User:
    return await user_service.confirm_user(user_id)


@users_router.post(
    "/{user_id}/resend-confirmation",
    operation_id="resendUserConfirmationMail",
    dependencies=[user_rate_limit("staff_resend_confirmation")],
)
async def resend_user_confirmation_mail(
    user_service: UserServiceDep, user_id: UUID
) -> None:
    await user_service.resend_confirmation_mail(user_id)


@users_router.patch(
    "/{user_id}",
    operation_id="updateCompanyUser",
    response_model=CompanyUserResponse,
)
async def update_company_user(
    user_service: UserServiceDep,
    user_id: UUID,
    request: UpdateCompanyUserRequest,
) -> User:
    return await user_service.update_company_user(user_id, request)


@users_router.delete(
    "/{user_id}",
    operation_id="deleteUser",
)
async def delete_user(user_service: UserServiceDep, user_id: UUID) -> None:
    await user_service.delete_user(user_id)


@router.post("/logout", operation_id="logoutUser")
async def logout_user(
    user_service: UserServiceDep,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    await user_service.logout_user(refresh_token)
    response.delete_cookie("refresh_token", samesite="lax")
    logger.info(f"User logout successful: {user_service.current_user.email}")
