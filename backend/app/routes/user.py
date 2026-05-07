import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Response

from app.core.deps import CsrfDep, UserServiceDep
from app.schemas.user import (
    CompanyUserResponse,
    CompanyUserResult,
    UpdateCompanyUserRequest,
    UpdateUserProfileRequest,
    UserResponse,
    UserResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"], dependencies=[CsrfDep])


@router.get("/me", operation_id="getCurrentUser", response_model=UserResponse)
async def get_current_user(user_service: UserServiceDep) -> UserResult:
    return await user_service.get_current_user()


@router.get(
    "/profile",
    operation_id="getUserProfile",
    response_model=CompanyUserResponse,
)
async def get_user_profile(user_service: UserServiceDep) -> CompanyUserResult:
    return await user_service.get_current_user_profile()


@router.patch(
    "/me",
    operation_id="updateUserProfile",
    response_model=CompanyUserResponse,
)
async def update_user_profile(
    user_service: UserServiceDep, request: UpdateUserProfileRequest
) -> CompanyUserResult:
    return await user_service.update_current_user_profile(
        request.first_name,
        request.last_name,
        request.phone_number,
    )


@router.get(
    "/companies",
    operation_id="getAllCompanyUsers",
    response_model=list[CompanyUserResponse],
)
async def get_all_company_users(
    user_service: UserServiceDep,
) -> list[CompanyUserResult]:
    return await user_service.get_company_users()


@router.get(
    "/admins",
    operation_id="getAllAdmins",
    response_model=list[UserResponse],
)
async def get_all_admins(user_service: UserServiceDep) -> list[UserResult]:
    return await user_service.get_admins()


@router.get(
    "/staff",
    operation_id="getAllStaff",
    response_model=list[UserResponse],
)
async def get_all_staff(user_service: UserServiceDep) -> list[UserResult]:
    return await user_service.get_staff()


@router.post("/send-confirmation-email", operation_id="sendConfirmationMail")
async def send_confirmation_mail(user_service: UserServiceDep) -> None:
    return await user_service.send_confirmation_mail()


@router.post("/confirm-email/{token}", operation_id="confirmEmail")
async def confirm_email(user_service: UserServiceDep, token: str) -> bool:
    return await user_service.confirm_email(token)


@router.get("/confirm-email/{token}", operation_id="validateConfirmEmailToken")
async def validate_confirm_email_token(
    user_service: UserServiceDep, token: str
) -> bool:
    return await user_service.validate_confirm_email_token(token)


@router.get(
    "/unconfirmed",
    operation_id="getUnconfirmedUsers",
    response_model=list[CompanyUserResponse],
)
async def get_unconfirmed_users(
    user_service: UserServiceDep,
) -> list[CompanyUserResult]:
    return await user_service.get_unconfirmed_users()


@router.post(
    "/confirm/{user_id}",
    operation_id="confirmUser",
    response_model=UserResponse,
)
async def confirm_user(user_service: UserServiceDep, user_id: UUID) -> UserResult:
    return await user_service.confirm_user(user_id)


@router.patch(
    "/{user_id}",
    operation_id="updateCompanyUser",
    response_model=CompanyUserResponse,
)
async def update_company_user(
    user_service: UserServiceDep,
    user_id: UUID,
    request: UpdateCompanyUserRequest,
) -> CompanyUserResult:
    return await user_service.update_company_user(
        user_id,
        request.email,
        request.first_name,
        request.last_name,
        request.phone_number,
        request.company_id,
    )


@router.delete(
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
