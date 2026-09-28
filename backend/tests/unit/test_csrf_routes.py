from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.csrf import CSRF_COOKIE_KEY
from app.core.deps import get_auth_service
from app.main import app
from app.services.auth_service import AuthService


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_auth_service] = lambda: AsyncMock(spec=AuthService)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver"
    ) as client:
        yield client
    app.dependency_overrides.clear()


async def test_csrf_token_endpoint_is_stable_for_a_valid_cookie(client: AsyncClient):
    first = await client.get("/api/csrftoken")
    second = await client.get("/api/csrftoken")

    assert first.json()["token"] == second.json()["token"]
    assert CSRF_COOKIE_KEY in first.cookies
    assert CSRF_COOKIE_KEY not in second.cookies


async def test_csrf_token_endpoint_issues_new_token_without_cookie(
    client: AsyncClient,
):
    first = await client.get("/api/csrftoken")
    client.cookies.clear()
    second = await client.get("/api/csrftoken")

    assert first.json()["token"] != second.json()["token"]
    assert CSRF_COOKIE_KEY in second.cookies


async def test_csrf_cookie_uses_explicit_attributes(client: AsyncClient):
    response = await client.get("/api/csrftoken")

    cookie_header = response.headers["set-cookie"]
    assert cookie_header.startswith(f"{CSRF_COOKIE_KEY}=")
    assert "SameSite=lax" in cookie_header
    assert "Secure" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/" in cookie_header


async def test_second_tab_does_not_invalidate_first_tab_token(client: AsyncClient):
    first_tab_token = (await client.get("/api/csrftoken")).json()["token"]
    await client.get("/api/csrftoken")

    response = await client.post(
        "/api/auth/refresh", headers={"X-CSRF-Token": first_tab_token}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "error.unauthenticated"


async def test_invalid_csrf_token_reports_machine_readable_code(client: AsyncClient):
    await client.get("/api/csrftoken")

    response = await client.post(
        "/api/auth/refresh", headers={"X-CSRF-Token": "not-the-real-token"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf.validation_failed"
