from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import grpc
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, update

from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    EmailTakenLocally,
    EmailUsed,
    KeycloakExchangeFailed,
    NotVisMember,
)
from app.core.utils import hash_str
from app.models.user import RefreshToken, User
from app.repositories.token_repository import REFRESH_TOKEN_REUSE_GRACE
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from tests.api.conftest import DEFAULT_PASSWORD

REGISTER_PAYLOAD = {
    "email": "new-company@example.com",
    "password": "brand-new-password",
    "first_name": "New",
    "last_name": "Company",
}


class MailRpcError(grpc.RpcError):
    pass


async def expire_rotation_grace(db_session: AsyncSession, token: str) -> None:
    await db_session.execute(
        update(RefreshToken)
        .where(col(RefreshToken.token) == hash_str(token))
        .values(rotated_at=datetime.now(timezone.utc) - REFRESH_TOKEN_REUSE_GRACE * 2)
    )
    await db_session.commit()


async def login(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    email: str,
    password: str = DEFAULT_PASSWORD,
):
    return await client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers=csrf_headers,
    )


async def test_register_returns_created_user(
    client: AsyncClient, csrf_headers: dict[str, str]
):
    response = await client.post(
        "/api/auth/register",
        json=REGISTER_PAYLOAD,
        headers=csrf_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == REGISTER_PAYLOAD["email"]
    assert body["is_company"] is True
    assert body["is_staff"] is False
    assert body["is_admin"] is False
    assert body["user_confirmed"] is False
    assert body["email_confirmed"] is False
    assert "password" not in body


async def test_register_reuses_email_of_soft_deleted_user(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    db_session: AsyncSession,
    create_user: Callable[..., Awaitable[User]],
):
    deleted = await create_user(email=REGISTER_PAYLOAD["email"])
    await UserRepository(db_session).delete_user(deleted)

    response = await client.post(
        "/api/auth/register",
        json=REGISTER_PAYLOAD,
        headers=csrf_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] != str(deleted.id)


async def test_register_with_existing_email_is_rejected(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
):
    await create_user(email=REGISTER_PAYLOAD["email"])

    response = await client.post(
        "/api/auth/register",
        json=REGISTER_PAYLOAD,
        headers=csrf_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.email_used"


async def test_register_without_csrf_header_is_rejected(
    client: AsyncClient, csrf_headers: dict[str, str]
):
    response = await client.post("/api/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 403
    assert response.json()["code"] == "csrf.validation_failed"


async def test_login_with_wrong_password_returns_invalid_credentials(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
):
    response = await login(client, csrf_headers, company_user.email, "wrong-password")

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "error.invalid_credentials"
    assert body["identifier"] == f"login:{company_user.email}"


async def test_login_sets_refresh_token_cookie(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
):
    response = await login(client, csrf_headers, company_user.email)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie


async def test_login_omits_secure_on_the_refresh_cookie_in_debug(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    debug_setting: Callable[[bool], None],
):
    debug_setting(True)

    response = await login(client, csrf_headers, company_user.email)

    assert response.status_code == 200
    assert "Secure" not in response.headers["set-cookie"]


async def test_keycloak_init_marks_the_state_cookie_secure(client: AsyncClient):
    response = await client.get("/api/auth/initiate")

    assert response.status_code == 200
    assert "oauth_state=" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]


async def test_keycloak_init_omits_secure_on_the_state_cookie_in_debug(
    client: AsyncClient, debug_setting: Callable[[bool], None]
):
    debug_setting(True)

    response = await client.get("/api/auth/initiate")

    assert response.status_code == 200
    assert "oauth_state=" in response.headers["set-cookie"]
    assert "Secure" not in response.headers["set-cookie"]


async def test_refresh_rotates_refresh_token_cookie(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
):
    login_response = await login(client, csrf_headers, company_user.email)
    refresh_token = login_response.cookies["refresh_token"]
    client.cookies.set("refresh_token", refresh_token)

    response = await client.post("/api/auth/refresh", headers=csrf_headers)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.cookies["refresh_token"] != refresh_token


async def test_refresh_with_rotated_token_inside_grace_succeeds(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
):
    login_response = await login(client, csrf_headers, company_user.email)
    refresh_token = login_response.cookies["refresh_token"]
    client.cookies.set("refresh_token", refresh_token)

    await client.post("/api/auth/refresh", headers=csrf_headers)
    client.cookies.set("refresh_token", refresh_token)
    response = await client.post("/api/auth/refresh", headers=csrf_headers)

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_with_rotated_token_after_grace_is_unauthenticated(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    db_session: AsyncSession,
):
    login_response = await login(client, csrf_headers, company_user.email)
    refresh_token = login_response.cookies["refresh_token"]
    client.cookies.set("refresh_token", refresh_token)

    await client.post("/api/auth/refresh", headers=csrf_headers)
    await expire_rotation_grace(db_session, refresh_token)
    client.cookies.set("refresh_token", refresh_token)
    response = await client.post("/api/auth/refresh", headers=csrf_headers)

    assert response.status_code == 401
    assert response.json()["code"] == "error.unauthenticated"


async def test_unconfirmed_user_cannot_use_company_route(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    user = await create_user(
        email="unconfirmed@example.com",
        company_name="Pending AG",
        user_confirmed=False,
    )

    response = await client.get(
        f"/api/kp/events/{uuid4()}/booth-zones/available",
        headers=await auth_headers(user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_confirmed"


async def test_company_user_cannot_use_staff_route(
    client: AsyncClient,
    company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    response = await client.get(
        "/api/user/companies", headers=await auth_headers(company_user)
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_staff_user_can_use_staff_route(
    client: AsyncClient,
    staff_user: User,
    company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    response = await client.get(
        "/api/user/companies", headers=await auth_headers(staff_user)
    )

    assert response.status_code == 200
    assert [entry["email"] for entry in response.json()] == [company_user.email]


async def test_password_reset_for_oauth_user_looks_like_success(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    mail_stub: AsyncMock,
):
    user = await create_user(email="oauth-only@example.com", password=None)

    response = await client.post(
        "/api/auth/reset-password",
        json={"email": user.email},
        headers=csrf_headers,
    )

    assert response.status_code == 200
    mail_stub.SendMail.assert_not_awaited()


async def test_password_reset_for_unknown_email_looks_like_success(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    response = await client.post(
        "/api/auth/reset-password",
        json={"email": "nobody@example.com"},
        headers=csrf_headers,
    )

    assert response.status_code == 200
    mail_stub.SendMail.assert_not_awaited()


async def test_password_reset_maps_grpc_failure_to_server_error(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.side_effect = MailRpcError()

    response = await client.post(
        "/api/auth/reset-password",
        json={"email": company_user.email},
        headers=csrf_headers,
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "gRPC call failed"


async def test_password_reset_sends_mail(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    mail_stub: AsyncMock,
):
    response = await client.post(
        "/api/auth/reset-password",
        json={"email": company_user.email},
        headers=csrf_headers,
    )

    assert response.status_code == 200
    mail_stub.SendMail.assert_awaited_once()


async def test_reset_with_short_password_returns_password_too_short(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    auth_service: AuthService,
):
    token = await auth_service.create_reset_password_token(company_user)

    response = await client.post(
        "/api/auth/reset",
        json={"token": token, "new_password": "short"},
        headers=csrf_headers,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "error.password_too_short"
    assert body["identifier"] == "reset_password:password_too_short"


async def test_reset_with_invalid_token_returns_token_invalid(
    client: AsyncClient,
    csrf_headers: dict[str, str],
):
    response = await client.post(
        "/api/auth/reset",
        json={"token": "unknown-token", "new_password": "long-enough-password"},
        headers=csrf_headers,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "error.token_invalid"
    assert body["identifier"] == "reset_password"


async def test_reset_hides_unexpected_error_details(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    async def explode(*_args: object, **_kwargs: object) -> bool:
        raise RuntimeError("connection to secret-db-host:5432 refused")

    monkeypatch.setattr(AuthService, "reset_password", explode)

    response = await client.post(
        "/api/auth/reset",
        json={"token": "any-token", "new_password": "long-enough-password"},
        headers=csrf_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.reset_password_failed"
    assert "secret-db-host" not in response.text


async def test_password_reset_is_rate_limited_per_client(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
):
    payload = {"email": company_user.email}
    limit = get_settings().RATE_LIMIT_MAX_REQUESTS

    accepted = [
        (
            await client.post(
                "/api/auth/reset-password", json=payload, headers=csrf_headers
            )
        ).status_code
        for _ in range(limit)
    ]
    blocked = await client.post(
        "/api/auth/reset-password", json=payload, headers=csrf_headers
    )

    assert accepted == [200] * limit
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "error.rate_limited"


async def keycloak_callback_response(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    exchange: Callable[..., Awaitable[str]],
    state: str = "matching-state",
):
    monkeypatch.setattr(AuthService, "keycloak_callback", exchange)
    client.cookies.set("oauth_state", state)

    return await client.get(f"/api/auth/callback?code=auth-code&state={state}")


def failing_exchange(error: AppError) -> Callable[..., Awaitable[str]]:
    async def exchange(*_args: object, **_kwargs: object) -> str:
        raise error

    return exchange


async def test_keycloak_callback_redirects_on_state_mismatch(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def exchange(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("token exchange must not run on a state mismatch")

    monkeypatch.setattr(AuthService, "keycloak_callback", exchange)
    client.cookies.set("oauth_state", "issued-state")

    response = await client.get("/api/auth/callback?code=auth-code&state=other-state")

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"{get_settings().VISIT_FRONTEND_SERVER_URL}/login?error=server.error"
    )
    assert 'oauth_state=""' in response.headers["set-cookie"]


async def test_keycloak_callback_redirects_on_exchange_failure(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    response = await keycloak_callback_response(
        client,
        monkeypatch,
        failing_exchange(KeycloakExchangeFailed("keycloak_callback:auth-code")),
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"{get_settings().VISIT_FRONTEND_SERVER_URL}/login?error=server.error"
    )
    assert "auth-code" not in response.headers["location"]


async def test_keycloak_callback_redirects_when_email_is_local(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    response = await keycloak_callback_response(
        client,
        monkeypatch,
        failing_exchange(EmailTakenLocally("keycloak:ada@example.com")),
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"{get_settings().VISIT_FRONTEND_SERVER_URL}"
        "/login?error=auth.email_taken_locally"
    )
    assert 'oauth_state=""' in response.headers["set-cookie"]


async def test_keycloak_callback_redirects_when_email_belongs_to_another_identity(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    response = await keycloak_callback_response(
        client,
        monkeypatch,
        failing_exchange(EmailUsed("keycloak:ada@example.com")),
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"{get_settings().VISIT_FRONTEND_SERVER_URL}/login?error=error.email_used"
    )
    assert 'oauth_state=""' in response.headers["set-cookie"]


async def test_keycloak_callback_redirects_without_vis_membership(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    response = await keycloak_callback_response(
        client, monkeypatch, failing_exchange(NotVisMember("keycloak:sub"))
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"{get_settings().VISIT_FRONTEND_SERVER_URL}/login?error=auth.not_vis_member"
    )


async def test_keycloak_callback_sets_refresh_cookie_on_success(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def exchange(*_args: object, **_kwargs: object) -> str:
        return "issued-refresh-token"

    response = await keycloak_callback_response(client, monkeypatch, exchange)

    assert response.status_code == 307
    assert response.headers["location"] == get_settings().VISIT_FRONTEND_SERVER_URL
    assert "refresh_token=issued-refresh-token" in response.headers["set-cookie"]
