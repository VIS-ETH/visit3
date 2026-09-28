from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.company import CompanyInvite
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from tests.api.conftest import KpSetup, move_event_into_the_past


async def test_delete_company_refused_while_upcoming_booking_exists(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    response = await client.delete(
        f"/api/company/{company_user.company_id}/delete-keep-users",
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.company_has_upcoming_bookings"


async def test_staff_booking_list_excludes_cascaded_company(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)
    await move_event_into_the_past(db_session, kp_setup.event_id)

    deletion = await client.delete(
        f"/api/company/{company_user.company_id}/delete-with-users",
        headers=staff_headers,
    )
    listing = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings",
        headers=staff_headers,
    )

    assert deletion.status_code == 200
    assert listing.status_code == 200
    assert listing.json() == []


async def test_setup_company_reuses_name_of_soft_deleted_company(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    csrf_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    company_repository = CompanyRepository(db_session)
    deleted = await company_repository.get_by_id(company_user.company_id)
    assert deleted is not None
    await company_repository.delete_company_keep_users(deleted)
    founder = await create_user(email="founder@example.com")

    response = await client.post(
        "/api/company/setup",
        json={"name": deleted.name},
        headers={**await auth_headers(founder), **csrf_headers},
    )

    assert response.status_code == 200
    assert response.json()["name"] == deleted.name
    assert response.json()["id"] != str(deleted.id)


async def test_setup_company_with_existing_name_is_rejected(
    client: AsyncClient,
    company_user: User,
    csrf_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    founder = await create_user(email="founder@example.com")

    response = await client.post(
        "/api/company/setup",
        json={"name": "Acme AG"},
        headers={**await auth_headers(founder), **csrf_headers},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.company_name_taken"


async def test_setup_company_response_hides_internal_columns(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    founder = await create_user(email="founder@example.com")

    response = await client.post(
        "/api/company/setup",
        json={"name": "Initech"},
        headers={**await auth_headers(founder), **csrf_headers},
    )

    assert response.status_code == 200
    assert set(response.json()) == {"id", "name"}


async def test_update_my_company_response_hides_internal_columns(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
):
    response = await client.patch(
        "/api/company/me",
        json={"name": "Acme Holding"},
        headers=company_headers,
    )

    assert response.status_code == 200
    assert set(response.json()) == {"id", "name"}


async def test_staff_booking_company_hides_internal_columns(
    client: AsyncClient,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    listing = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings",
        headers=staff_headers,
    )

    assert listing.status_code == 200
    assert set(listing.json()[0]["company"]) == {"id", "name"}


async def test_second_invite_for_the_same_email_is_refused(
    client: AsyncClient,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    payload = {"email": "invitee@example.com"}

    first = await client.post(
        "/api/company/invite", json=payload, headers=company_headers
    )
    second = await client.post(
        "/api/company/invite", json=payload, headers=company_headers
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["code"] == "error.company_invite_pending"
    mail_stub.SendMail.assert_awaited_once()


async def test_invite_can_be_resent_once_the_pending_one_expired(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
):
    payload = {"email": "invitee@example.com"}
    await client.post("/api/company/invite", json=payload, headers=company_headers)
    invite = (await db_session.execute(select(CompanyInvite))).scalar_one()
    invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.add(invite)
    await db_session.commit()

    response = await client.post(
        "/api/company/invite", json=payload, headers=company_headers
    )

    assert response.status_code == 200
