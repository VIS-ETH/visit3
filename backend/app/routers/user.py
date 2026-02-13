from typing import List
from fastapi import APIRouter
from app.core.deps import CsrfDep, UserServiceDep
from app.models.user import User
from app.core.exceptions import not_allowed_e

router = APIRouter(prefix="/user", tags=["user"], dependencies=[CsrfDep])


@router.get("/me", operation_id="readUsersMe")
def read_users_me(user_service: UserServiceDep) -> User:
    if not user_service.current_user.is_company:
        raise not_allowed_e
    return user_service.current_user


@router.get("/list", operation_id="listUsers")
async def list_users(user_service: UserServiceDep) -> List[User]:
    return None


@router.post("/logout", operation_id="logoutUser")
async def logout_user(user_service: UserServiceDep) -> None:
    return None
