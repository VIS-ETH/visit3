from typing import Annotated, List
import logging
from uuid import UUID

from fastapi import APIRouter, Cookie

from app.core.deps import CsrfDep, UserServiceDep
from app.core.exceptions import TokenInvalid
from app.models.user import User
from app.schemas.user import CompanyUserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"], dependencies=[CsrfDep])


@router.get("/me", operation_id="readUsersMe")
async def read_users_me(user_service: UserServiceDep) -> User:
    return await user_service.get_current_user()


@router.get("/companies", operation_id="getAllCompanyUsers")
async def get_all_company_users(user_service: UserServiceDep) -> list[CompanyUserResponse]:
    return await user_service.get_company_users()


@router.get("/admins", operation_id="getAllAdmins")
async def get_all_admins(user_service: UserServiceDep) -> list[User]:
    return await user_service.get_admins()


@router.get("/staff", operation_id="getAllStaff")
async def get_all_staff(user_service: UserServiceDep) -> list[User]:
    return await user_service.get_staff()


@router.post("/send-confirmation-email", operation_id="sendConfirmationMail")
async def send_confirmation_mail(user_service: UserServiceDep) -> None:
    return await user_service.send_confirmation_mail()


@router.post("/confirm-email/{token}", operation_id="confirmEmail")
async def confirm_email(user_service: UserServiceDep, token: str):
    return await user_service.confirm_email(token)


@router.get("/confirm-email/{token}", operation_id="validateConfirmEmailToken")
async def validate_confirm_email_token(user_service: UserServiceDep, token: str) -> bool:
    return await user_service.validate_confirm_email_token(token)


@router.get("/unconfirmed", operation_id="getUnconfirmedUsers")
async def get_unconfirmed_users(
    user_service: UserServiceDep,
) -> List[CompanyUserResponse]:
    return await user_service.get_unconfirmed_users()


@router.post("/confirm/{user_id}", operation_id="confirmUser")
async def confirm_user(user_service: UserServiceDep, user_id: UUID) -> User:
    return await user_service.confirm_user(user_id)


@router.delete(
    "/{user_id}",
    operation_id="deleteUser",
)
async def delete_user(user_service: UserServiceDep, user_id: UUID):
    await user_service.delete_user(user_id)


@router.post("/logout", operation_id="logoutUser")
async def logout_user(
    user_service: UserServiceDep, refresh_token: Annotated[str | None, Cookie()] = None
):
    if not refresh_token:
        logger.warning(
            f"Logout failed - no refresh token: {user_service.current_user.email}"
        )
        raise TokenInvalid(f"logout:{user_service.current_user.id}")

    await user_service.logout_user(refresh_token)
    logger.info(f"User logout successful: {user_service.current_user.email}")
    return None
