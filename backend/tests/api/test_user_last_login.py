from datetime import datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import AuthService
from tests.api.test_auth_routes import login
from tests.api.test_sso_sessions import claims, sso_user


async def last_login_of(db_session: AsyncSession, user: User) -> datetime | None:
    await db_session.refresh(user)
    return user.last_login_at


async def listed_user(
    client: AsyncClient, staff_headers: dict[str, str], email: str
) -> dict[str, str | None]:
    response = await client.get(f"/api/users?query={email}", headers=staff_headers)
    assert response.status_code == 200
    return response.json()["items"][0]


async def test_a_new_user_has_never_logged_in(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    item = await listed_user(client, staff_headers, company_user.email)

    assert item["last_login_at"] is None
    assert datetime.fromisoformat(str(item["created_at"])) == company_user.created_at


async def test_a_password_login_is_recorded(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    staff_headers: dict[str, str],
    db_session: AsyncSession,
):
    response = await login(client, csrf_headers, company_user.email)

    assert response.status_code == 200
    last_login = await last_login_of(db_session, company_user)
    assert last_login is not None
    item = await listed_user(client, staff_headers, company_user.email)
    assert datetime.fromisoformat(str(item["last_login_at"])) == last_login


async def test_a_failed_login_is_not_recorded(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    db_session: AsyncSession,
):
    await login(client, csrf_headers, company_user.email, "wrong-password")

    assert await last_login_of(db_session, company_user) is None


async def test_a_login_link_is_recorded(
    client: AsyncClient,
    auth_service: AuthService,
    company_user: User,
    db_session: AsyncSession,
):
    link = await auth_service.create_login_link(company_user, "/")

    await client.get(f"/api/auth/link/{link.rsplit('/', 1)[1]}")

    assert await last_login_of(db_session, company_user) is not None


async def test_an_sso_login_is_recorded(
    auth_service: AuthService, db_session: AsyncSession
):
    await auth_service.login_keycloak_user(claims(), "kc-refresh-1")

    assert (await sso_user(db_session)).last_login_at is not None


async def test_a_session_refresh_is_not_a_login(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    db_session: AsyncSession,
):
    await login(client, csrf_headers, company_user.email)
    first_login = await last_login_of(db_session, company_user)

    refreshed = await client.post("/api/auth/refresh", headers=csrf_headers)

    assert refreshed.status_code == 200
    assert await last_login_of(db_session, company_user) == first_login
