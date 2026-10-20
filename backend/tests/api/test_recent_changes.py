from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.company import Company
from app.models.kp_event import KpEventBooking, KpEventBookingService
from app.models.user import User
from tests.api.conftest import KpSetup
from tests.api.test_auth_routes import login

LONG_AGO = datetime.now(timezone.utc) - timedelta(days=30)
NEWCOMER_EMAIL = "newcomer@example.com"


async def backdate(db_session: AsyncSession, *models: type, ids: list[UUID]) -> None:
    for model in models:
        rows = await db_session.execute(select(model).where(col(model.id).in_(ids)))
        for row in rows.scalars().all():
            row.created_at = LONG_AGO
            if hasattr(row, "updated_at"):
                row.updated_at = LONG_AGO
            db_session.add(row)
    await db_session.commit()


async def mark_seen_at(db_session: AsyncSession, user: User, seen_at: datetime) -> None:
    user.changes_seen_at = seen_at
    db_session.add(user)
    await db_session.commit()


async def recent_changes(
    client: AsyncClient, headers: dict[str, str]
) -> dict[str, object]:
    response = await client.get("/api/changes", headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()


def names(items: object, key: str) -> list[str]:
    assert isinstance(items, list)
    return [str(item[key]) for item in items]


@pytest.fixture
async def old_world(
    db_session: AsyncSession,
    admin_user: User,
    company_user: User,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
) -> dict[str, str]:
    booking = (await register_booking(company_headers, kp_setup)).json()
    services = await db_session.execute(
        select(KpEventBookingService.id).where(
            col(KpEventBookingService.booking_id) == UUID(booking["id"])
        )
    )
    await backdate(
        db_session,
        User,
        Company,
        KpEventBooking,
        KpEventBookingService,
        ids=[
            admin_user.id,
            company_user.id,
            company_user.company_id or admin_user.id,
            UUID(booking["id"]),
            *services.scalars().all(),
        ],
    )
    await mark_seen_at(
        db_session, admin_user, datetime.now(timezone.utc) - timedelta(days=1)
    )
    return {"booking_id": booking["id"]}


async def test_changes_are_for_staff_only(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.get("/api/changes", headers=company_headers)

    assert response.status_code == 403


async def test_nothing_changed_since_the_last_visit(
    client: AsyncClient, staff_headers: dict[str, str], old_world: dict[str, str]
):
    changes = await recent_changes(client, staff_headers)

    assert changes["new_users_total"] == 0
    assert changes["new_companies_total"] == 0
    assert changes["new_bookings_total"] == 0
    assert changes["changed_bookings_total"] == 0


async def test_new_accounts_companies_and_bookings_are_listed(
    client: AsyncClient,
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
    old_world: dict[str, str],
):
    newcomer = await create_user(email=NEWCOMER_EMAIL, company_name="Neu AG")
    await register_booking({**await auth_headers(newcomer), **csrf_headers}, kp_setup)

    changes = await recent_changes(client, staff_headers)

    assert names(changes["new_users"], "email") == [NEWCOMER_EMAIL]
    assert names(changes["new_companies"], "name") == ["Neu AG"]
    assert names(changes["new_bookings"], "company_name") == ["Neu AG"]
    assert changes["changed_bookings_total"] == 0


async def test_a_changed_booking_is_listed(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    old_world: dict[str, str],
):
    added = await client.post(
        f"/api/kp/bookings/{old_world['booking_id']}/services",
        json={"services": [{"service_id": kp_setup.service_id, "quantity": 1}]},
        headers=company_headers,
    )

    changes = await recent_changes(client, staff_headers)

    assert added.status_code == 200, added.json()
    assert names(changes["changed_bookings"], "id") == [old_world["booking_id"]]
    assert changes["new_bookings_total"] == 0


async def test_marking_changes_as_seen_clears_them(
    client: AsyncClient,
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    old_world: dict[str, str],
):
    await create_user(email=NEWCOMER_EMAIL)

    marked = await client.post("/api/changes/seen", headers=staff_headers)
    changes = await recent_changes(client, staff_headers)

    assert marked.status_code == 204
    assert changes["new_users_total"] == 0


async def test_the_user_list_filters_new_users(
    client: AsyncClient,
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    old_world: dict[str, str],
):
    await create_user(email=NEWCOMER_EMAIL)

    response = await client.get("/api/users?filter=new", headers=staff_headers)

    assert names(response.json()["items"], "email") == [NEWCOMER_EMAIL]


async def test_the_company_list_filters_changed_companies(
    client: AsyncClient,
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    old_world: dict[str, str],
):
    await create_user(email=NEWCOMER_EMAIL, company_name="Neu AG")

    changed = await client.get(
        "/api/companies?only_changes=true", headers=staff_headers
    )
    everything = await client.get("/api/companies", headers=staff_headers)

    assert names(changed.json()["items"], "name") == ["Neu AG"]
    assert len(everything.json()["items"]) == 2


async def test_the_staff_booking_list_reports_when_a_booking_changed(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    old_world: dict[str, str],
):
    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings", headers=staff_headers
    )

    booking = response.json()[0]
    assert datetime.fromisoformat(booking["changed_at"]) < datetime.now(
        timezone.utc
    ) - timedelta(days=7)


async def test_a_login_keeps_the_previous_login(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    db_session: AsyncSession,
):
    await login(client, csrf_headers, company_user.email)
    await db_session.refresh(company_user)
    first = company_user.last_login_at

    await login(client, csrf_headers, company_user.email)
    await db_session.refresh(company_user)

    assert company_user.previous_login_at == first
    assert company_user.last_login_at != first
