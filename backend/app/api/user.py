from datetime import datetime, timezone
from typing import Annotated, List
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
import grpc
from app.deps import Context, UserContext
from app.schemas.user import ForgetPasswordRequest, RegisterUserRequest, ResetPasswordRequest, Token
from app.models.user import User
from app.crud.user import (
    change_password,
    create_user,
    get_user_by_id,
    get_users,
    revoke_refresh_tokens,
    check_forget_password_token
)
from app.core.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    hash_password,
    set_refresh_cookie,
    verify_refresh_token,
    create_forget_password_token,
)
from app.utils.exceptions import unauth_e
from sqlalchemy.exc import IntegrityError
from app.core.mail import construct_mail
from app.config import get_settings

router = APIRouter(prefix="/user", tags=["users"])


@router.get("/me", operation_id="readUsersMe")
def read_users_me(ctx: UserContext) -> User:
    return ctx.user


@router.post("/register", operation_id="registerUser")
async def register_user(ctx: Context, request: RegisterUserRequest) -> User:
    user = User.model_validate(request)

    if len(user.password) < 10:
        raise HTTPException(status_code=400, detail="register.password.min")

    user.password = hash_password(user.password)

    user.is_admin = False
    user.is_staff = False
    user.is_company = True

    try:
        return await create_user(ctx.session, user)
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail="register.email.used")
    except Exception as e:
        raise HTTPException(status_code=400, detail="register.failed")


@router.get("/list", operation_id="listUsers")
async def list_users(ctx: UserContext) -> List[User]:
    ctx.verify_admin()
    return await get_users(ctx.session)


@router.post("/login", operation_id="loginUser")
async def login_user(
    ctx: Context,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = await authenticate_user(ctx.session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="password.wrong")
    access_token = create_access_token(user)

    raw_refresh_token = await create_refresh_token(ctx.session, user)

    set_refresh_cookie(response, raw_refresh_token)

    return Token(access_token=access_token, token_type="bearer")


@router.post("/refresh", operation_id="refreshUser")
async def refresh_user(
    ctx: Context,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Token:
    if not refresh_token:
        raise unauth_e

    token = await verify_refresh_token(ctx.session, refresh_token)

    if not token or token.is_revoked or datetime.now(timezone.utc) > token.expires_at:
        raise unauth_e

    user = await get_user_by_id(ctx.session, token.user_id)

    if not user:
        raise unauth_e

    access_token = create_access_token(user)

    raw_refresh_token = await create_refresh_token(ctx.session, user)

    set_refresh_cookie(response, raw_refresh_token)

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout", operation_id="logoutUser")
async def logout_user(ctx: UserContext) -> None:
    await revoke_refresh_tokens(ctx.session, ctx.user)
    return None


@router.post("/forget_password", operation_id="forgetPassword")
async def forget_password(ctx: Context, request: ForgetPasswordRequest):
    token = await create_forget_password_token(ctx.session, request.email)

    if not token:
        return None

    request = construct_mail(
        [request.email],
        "VISIT Reset Password",
        plain_text=f"Go to this link to reset your password {get_settings().FRONTEND_SERVER}/reset/{token}",
    )
    try:
        await ctx.mail_stub.SendMail(request)
        return None
    except grpc.RpcError as e:
        print(f"gRPC Error: {e.code()} - {e.details()}")
        raise HTTPException(status_code=500, detail="gRPC call failed")
    
@router.get("/validate_reset/{token}", operation_id="validResetPassword")
async def validate_reset_token(ctx: Context, token: str) -> bool:
    return await check_forget_password_token(ctx.session, token)
    
@router.post("/reset", operation_id="resetPassword")
async def reset_password(ctx: Context, request: ResetPasswordRequest) -> bool:
    try:
        return await change_password(ctx.session, request.token, hash_password(request.new_password))
    except Exception as e:
        raise HTTPException(status_code=400, detail="reset_password.error")
    
    


