import secrets
import logging
from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.user import (
    ForgetPasswordRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
    Token,
)
from app.models.user import User
from app.core.config import get_settings
from app.core.exceptions import (
    KeycloakExchangeFailed,
    PasswordWrong,
    ResetPasswordError,
    TokenInvalid,
    Unauthenticated,
    UserNotFound,
)
from app.core.deps import CsrfDep, AuthServiceDep
from app.services.auth_service import REFRESH_TOKEN_EXPIRE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[CsrfDep])


def set_refresh_cookie(response: Response, raw_refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(REFRESH_TOKEN_EXPIRE.total_seconds()),
    )


@router.post("/register", operation_id="registerUser")
async def register_user(
    auth_service: AuthServiceDep,
    request: RegisterUserRequest,
) -> User:
    user = User(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        company_id=request.company_id,
        phone_number=request.phone_number,
    )

    return await auth_service.register_user(user, request.company_name)


@router.post("/login", operation_id="loginUser")
async def login_user(
    auth_service: AuthServiceDep,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    (access_token, refresh_token) = await auth_service.login_user(
        form_data.username, form_data.password
    )

    set_refresh_cookie(response, refresh_token)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/refresh", operation_id="refreshUser")
async def refresh_user(
    auth_service: AuthServiceDep,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Token:
    try:
        (access_token, refresh_token) = await auth_service.refresh_user(refresh_token)

        set_refresh_cookie(response, refresh_token)
        return Token(access_token=access_token, token_type="bearer")
    except TokenInvalid as e:
        raise Unauthenticated(e.identifier)


@router.post("/forget-password", operation_id="forgetPassword")
async def forget_password(auth_service: AuthServiceDep, request: ForgetPasswordRequest):
    try:
        return await auth_service.forget_password(request.email)
    except Exception as e:
        raise HTTPException(status_code=500, detail="gRPC call failed")


@router.get("/reset/{token}", operation_id="validResetPassword")
async def validate_reset_token(auth_service: AuthServiceDep, token: str) -> bool:
    return await auth_service.validate_reset_token(token)


@router.post("/reset", operation_id="resetPassword")
async def reset_password(
    request: ResetPasswordRequest, auth_service: AuthServiceDep
) -> bool:
    try:
        result = await auth_service.reset_password(request.token, request.new_password)
        logger.info("Password reset successful")
        return result
    except Exception as e:
        raise ResetPasswordError(str(e))


@router.get("/callback", operation_id="keycloakCallback")
async def keycloak_callback(
    auth_service: AuthServiceDep,
    code: str,
    state: str,
    oauth_state: str = Cookie(None),
):
    if not oauth_state or state != oauth_state:
        raise HTTPException(
            status_code=400, detail="State mismatch. CSRF suspected.")

    try:
        refresh_token = await auth_service.keycloak_callback(code)
    except KeycloakExchangeFailed as e:
        raise HTTPException(
            status_code=400, detail=f"Exchange failed: {e.identifier}")

    response = RedirectResponse(url=get_settings().FRONTEND_SERVER)

    response.delete_cookie("oauth_state")

    set_refresh_cookie(response, refresh_token)

    return response


@router.get("/initiate", operation_id="keycloakInit")
def keycloak_init(response: Response) -> str:
    state = secrets.token_urlsafe(32)

    response.set_cookie(
        key="oauth_state", value=state, httponly=True, max_age=600, samesite="lax"
    )

    login_url = (
        f"{get_settings().KEYCLOAK_AUTH_URL}"
        f"?client_id={get_settings().KEYCLOAK_CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid"
        f"&redirect_uri={get_settings().KEYCLOAK_CALLBACK}"
        f"&state={state}"
    )

    return login_url
