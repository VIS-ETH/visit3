from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.config import get_settings
from app.core.utils import hash_str
from app.models.auth_tokens import LoginLinkToken
from app.models.user import User
from app.services.auth_service import AuthService

FRONTEND = get_settings().VISIT_FRONTEND_SERVER_URL
BOOKING_PATH = "/kp/1234/booking"
INVALID_LINK_LOCATION = f"{FRONTEND}/login?error=auth.link_invalid"


def token_of(login_url: str) -> str:
    return login_url.rsplit("/", 1)[1]


async def stored_token(db_session: AsyncSession, token: str) -> LoginLinkToken:
    statement = select(LoginLinkToken).where(
        col(LoginLinkToken.token) == hash_str(token)
    )
    return (await db_session.execute(statement)).scalar_one()


@pytest.fixture
async def login_url(auth_service: AuthService, company_user: User) -> str:
    return await auth_service.create_login_link(company_user, BOOKING_PATH)


async def test_login_link_url_points_at_the_frontend(login_url: str):
    assert login_url.startswith(f"{FRONTEND}/auth/link/")


async def test_valid_link_logs_in_and_redirects_to_the_target(
    client: AsyncClient, login_url: str
):
    response = await client.get(f"/api/auth/link/{token_of(login_url)}")

    assert response.status_code == 303
    assert response.headers["location"] == f"{FRONTEND}{BOOKING_PATH}"
    assert response.cookies["refresh_token"]


async def test_the_issued_refresh_cookie_works_like_a_password_login(
    client: AsyncClient, login_url: str, csrf_headers: dict[str, str]
):
    link_response = await client.get(f"/api/auth/link/{token_of(login_url)}")
    client.cookies.update(link_response.cookies)

    refreshed = await client.post("/api/auth/refresh", headers=csrf_headers)

    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


async def test_a_link_can_only_be_used_once(client: AsyncClient, login_url: str):
    await client.get(f"/api/auth/link/{token_of(login_url)}")

    second = await client.get(f"/api/auth/link/{token_of(login_url)}")

    assert second.status_code == 303
    assert second.headers["location"] == INVALID_LINK_LOCATION


async def test_unknown_token_redirects_to_the_login_error(client: AsyncClient):
    response = await client.get("/api/auth/link/not-a-token")

    assert response.status_code == 303
    assert response.headers["location"] == INVALID_LINK_LOCATION


async def test_expired_link_redirects_to_the_login_error(
    client: AsyncClient, db_session: AsyncSession, login_url: str
):
    link_token = await stored_token(db_session, token_of(login_url))
    link_token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.add(link_token)
    await db_session.commit()

    response = await client.get(f"/api/auth/link/{token_of(login_url)}")

    assert response.headers["location"] == INVALID_LINK_LOCATION


async def test_password_reset_revokes_open_links(
    client: AsyncClient,
    auth_service: AuthService,
    company_user: User,
    login_url: str,
):
    reset_token = await auth_service.create_reset_password_token(company_user)
    await auth_service.reset_password(reset_token, "a-brand-new-password")

    response = await client.get(f"/api/auth/link/{token_of(login_url)}")

    assert response.headers["location"] == INVALID_LINK_LOCATION


async def test_absolute_target_paths_are_rejected_at_creation(
    client: AsyncClient, auth_service: AuthService, company_user: User
):
    absolute = await auth_service.create_login_link(company_user, "https://evil.test")

    response = await client.get(f"/api/auth/link/{token_of(absolute)}")

    assert response.headers["location"] == f"{FRONTEND}/"


async def test_protocol_relative_target_paths_are_rejected_at_creation(
    client: AsyncClient, auth_service: AuthService, company_user: User
):
    protocol_relative = await auth_service.create_login_link(
        company_user, "//evil.test"
    )

    response = await client.get(f"/api/auth/link/{token_of(protocol_relative)}")

    assert response.headers["location"] == f"{FRONTEND}/"
