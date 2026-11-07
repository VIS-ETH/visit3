from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.models.user import User
from app.services.auth_service import AuthService
from tests.api.conftest import DEFAULT_PASSWORD

IMPERSONATE = "X-Impersonate-User-Id"


async def login(client: AsyncClient, csrf_headers: dict[str, str], email: str) -> str:
    response = await client.post(
        "/api/auth/login",
        data={"username": email, "password": DEFAULT_PASSWORD},
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.cookies["refresh_token"]


async def refresh(
    client: AsyncClient, csrf_headers: dict[str, str], token: str
) -> tuple[int, str | None]:
    client.cookies.set("refresh_token", token)
    response = await client.post("/api/auth/refresh", headers=csrf_headers)
    return response.status_code, response.cookies.get("refresh_token")


async def test_logging_out_while_impersonating_ends_the_admins_own_session(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    admin_user: User,
    company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    token = await login(client, csrf_headers, admin_user.email)
    client.cookies.set("refresh_token", token)
    headers = {
        **await auth_headers(admin_user),
        **csrf_headers,
        IMPERSONATE: str(company_user.id),
    }

    logout = await client.post("/api/user/logout", headers=headers)

    assert logout.status_code == 200
    status, _ = await refresh(client, csrf_headers, token)
    assert status == 401


async def test_logging_out_ends_tokens_minted_by_a_parallel_refresh(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    original = await login(client, csrf_headers, company_user.email)
    _, first_tab = await refresh(client, csrf_headers, original)
    _, second_tab = await refresh(client, csrf_headers, original)
    assert first_tab is not None and second_tab is not None
    assert first_tab != second_tab
    client.cookies.set("refresh_token", first_tab)

    await client.post(
        "/api/user/logout",
        headers={**await auth_headers(company_user), **csrf_headers},
    )

    status, _ = await refresh(client, csrf_headers, second_tab)
    assert status == 401


def keycloak_claims(sub: str, email: str) -> dict[str, Any]:
    return {
        "sub": sub,
        "email": email,
        "given_name": "Ada",
        "family_name": "Lovelace",
        "resource_access": {
            get_settings().SIP_AUTH_OIDC_CLIENT_ID: {"roles": ["vis-active"]}
        },
    }


async def test_an_sso_email_change_onto_a_local_account_redirects_to_the_login_error(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    auth_service: AuthService,
    monkeypatch: pytest.MonkeyPatch,
):
    await create_user(email="taken@example.com", company_name="Local AG")
    await auth_service.map_keycloak_to_user(keycloak_claims("sso-1", "ada@example.com"))

    async def callback(self: AuthService, code: str, verifier: str) -> str:
        return await self.login_keycloak_user(
            keycloak_claims("sso-1", "taken@example.com")
        )

    monkeypatch.setattr(AuthService, "keycloak_callback", callback)
    client.cookies.set("oauth_state", "state")
    client.cookies.set("oauth_verifier", "verifier")

    response = await client.get("/api/auth/callback?code=c&state=state")

    assert response.status_code == 303
    assert response.headers["location"].endswith(
        "/login?error=auth.email_taken_locally"
    )
