from typing import Annotated, List
from fastapi import APIRouter, Cookie
from app.core.deps import CsrfDep, UserServiceDep
from app.models.user import User
from app.core.exceptions import TokenInvalid

router = APIRouter(prefix="/user", tags=["user"], dependencies=[CsrfDep])


@router.get("/me", operation_id="readUsersMe")
async def read_users_me(user_service: UserServiceDep) -> User:
    return await user_service.get_current_user()


@router.get("/list", operation_id="listUsers")
async def list_users(user_service: UserServiceDep) -> List[User]:
    return None

@router.post("/send_confirmation_email", operation_id="sendConfirmationMail")
async def send_confirmation_mail(user_service: UserServiceDep) -> None:
    return await user_service.send_confirmation_mail()

@router.get("/confirm_email/{token}", operation_id="confirmEmail")
async def confirm_email(user_service: UserServiceDep, token: str):
    return await user_service.confirm_email(token)

@router.post("/logout", operation_id="logoutUser")
async def logout_user(user_service: UserServiceDep, 
    refresh_token: Annotated[str | None, Cookie()] = None):
    
    if not refresh_token:
        raise TokenInvalid(user_service.current_user.email)
    
    await user_service.logout_user(refresh_token)
    return None
    
