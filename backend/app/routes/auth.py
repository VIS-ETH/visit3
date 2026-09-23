import logging
import secrets
from typing import Annotated

import grpc
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import get_settings
from app.core.cookies import secure_cookies
from app.core.deps import AuthServiceDep, CsrfDep
from app.core.exceptions import (
    AppError,
    EmailTakenLocally,
    EmailUsed,
    KeycloakExchangeFailed,
    NotVisMember,
    ResetPasswordError,
    TokenInvalid,
    Unauthenticated,
)
from app.core.rate_limit import client_rate_limit
from app.models.user import User
from app.repositories.token_repository import REFRESH_TOKEN_EXPIRE
from app.schemas.user import (
    PasswordResetRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
    Token,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[CsrfDep])

GENERIC_LOGIN_ERROR = "server.error"
LOGIN_LINK_ERROR = "auth.link_invalid"


def set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=secure_cookies(),
        samesite="lax",
        max_age=int(REFRESH_TOKEN_EXPIRE.total_seconds()),
    )


@router.post(
    "/register",
    operation_id="registerUser",
    response_model=UserResponse,
)
async def register_user(
    auth_service: AuthServiceDep,
    request: RegisterUserRequest,
) -> User:
    user = User(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number,
    )

    return await auth_service.register_user(user, request.invite_token)


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
        if refresh_token is None:
            raise TokenInvalid("refresh:no_token")

        (access_token, refresh_token) = await auth_service.refresh_user(refresh_token)

        set_refresh_cookie(response, refresh_token)
        return Token(access_token=access_token, token_type="bearer")
    except TokenInvalid as e:
        raise Unauthenticated(e.identifier)


@router.post(
    "/reset-password",
    operation_id="requestPasswordReset",
    dependencies=[client_rate_limit("reset_password")],
)
async def request_password_reset(
    auth_service: AuthServiceDep, request: PasswordResetRequest
) -> None:
    try:
        return await auth_service.request_password_reset(request.email)
    except grpc.RpcError:
        raise HTTPException(status_code=500, detail="gRPC call failed")


@router.get("/reset/{token}", operation_id="validResetPassword")
async def validate_reset_token(auth_service: AuthServiceDep, token: str) -> bool:
    return await auth_service.validate_reset_token(token)


@router.post("/reset", operation_id="resetPassword")
async def reset_password(
    request: ResetPasswordRequest, auth_service: AuthServiceDep
) -> bool:
    try:
        return await auth_service.reset_password(request.token, request.new_password)
    except AppError:
        raise
    except Exception:
        logger.exception("Password reset failed unexpectedly")
        raise ResetPasswordError("reset_password:unexpected")


@router.get("/link/{token}", operation_id="loginWithLink")
async def login_with_link(auth_service: AuthServiceDep, token: str) -> RedirectResponse:
    frontend = get_settings().VISIT_FRONTEND_SERVER_URL
    try:
        link = await auth_service.consume_login_link(token)
    except TokenInvalid:
        return RedirectResponse(
            f"{frontend}/login?error={LOGIN_LINK_ERROR}", status_code=303
        )

    response = RedirectResponse(f"{frontend}{link.target_path}", status_code=303)
    set_refresh_cookie(response, link.refresh_token)
    return response


def login_error_redirect(code: str) -> RedirectResponse:
    response = RedirectResponse(
        f"{get_settings().VISIT_FRONTEND_SERVER_URL}/login?error={code}",
        status_code=303,
    )
    response.delete_cookie("oauth_state")
    return response


@router.get("/callback", operation_id="keycloakCallback")
async def keycloak_callback(
    auth_service: AuthServiceDep,
    code: str,
    state: str,
    oauth_state: str = Cookie(None),
) -> RedirectResponse:
    if not oauth_state or state != oauth_state:
        return login_error_redirect(GENERIC_LOGIN_ERROR)

    try:
        refresh_token = await auth_service.keycloak_callback(code)
    except (EmailTakenLocally, EmailUsed, NotVisMember) as e:
        return login_error_redirect(e.code)
    except KeycloakExchangeFailed:
        return login_error_redirect(GENERIC_LOGIN_ERROR)

    response = RedirectResponse(url=get_settings().VISIT_FRONTEND_SERVER_URL)

    response.delete_cookie("oauth_state")

    set_refresh_cookie(response, refresh_token)

    return response


@router.get("/initiate", operation_id="keycloakInit")
def keycloak_init(response: Response) -> str:
    state = secrets.token_urlsafe(32)

    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=secure_cookies(),
        max_age=600,
        samesite="lax",
    )

    login_url = (
        f"{get_settings().SIP_AUTH_OIDC_AUTH_ENDPOINT}"
        f"?client_id={get_settings().SIP_AUTH_OIDC_CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid"
        f"&redirect_uri={get_settings().KEYCLOAK_CALLBACK}"
        f"&state={state}"
    )

    return login_url
