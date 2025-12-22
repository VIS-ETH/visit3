from datetime import datetime, timezone
from typing import Annotated
import uuid
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.deps import CurrentUserDep, DbSessionDep
from app.schemas.user import Token, UserCreate
from app.models.user import User
from app.crud.user import create_user, get_user_by_id, get_users, revoke_refresh_tokens
from app.core.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    hash_password,
    set_refresh_cookie,
    verify_refresh_token,
)

router = APIRouter(prefix="/users")

unauth_e = HTTPException(
    status_code=401,
    detail="Unauthenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


@router.get("/me")
def read_users_me(current_user: CurrentUserDep):
    if not current_user:
        raise unauth_e
    return current_user


@router.post("/register")
async def register_user(session: DbSessionDep, user_create: UserCreate):
    user = User.model_validate(user_create)

    if len(user.password) < 10:
        raise HTTPException(
            status_code=400, detail="Password has to be longer than 10 characters"
        )

    user.password = hash_password(user.password)

    try:
        return await create_user(session, user)
    except:
        raise HTTPException(status_code=400, detail="Creating user failed")


@router.get("/list")
async def list_users(session: DbSessionDep):
    return await get_users(session)


@router.post("/login")
async def login_user(
    session: DbSessionDep,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise unauth_e
    access_token = create_access_token(data={"sub": user.email})

    raw_refresh_token = await create_refresh_token(session, user)

    set_refresh_cookie(response, raw_refresh_token)

    return Token(access_token=access_token, token_type="bearer")


@router.post("/refresh")
async def refresh_user(
    session: DbSessionDep,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if not refresh_token:
        raise unauth_e

    token = await verify_refresh_token(session, refresh_token)

    if not token or token.is_revoked or datetime.now(timezone.utc) > token.expires_at:
        raise unauth_e

    user = await get_user_by_id(session, token.user_id)

    if not user:
        raise unauth_e

    access_token = create_access_token(data={"sub": user.email})

    raw_refresh_token = await create_refresh_token(session, user)

    set_refresh_cookie(response, raw_refresh_token)

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout_user(session: DbSessionDep, current_user: CurrentUserDep):
    await revoke_refresh_tokens(session, current_user)
    return None
