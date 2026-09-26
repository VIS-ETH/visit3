from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.company_repository import CompanyRepository

INVITE_TOKEN = "welcome-token"
NEWCOMER_EMAIL = "newcomer@example.com"


async def members(
    client: AsyncClient, headers: dict[str, str], company_id: object
) -> dict[str, dict[str, Any]]:
    response = await client.get(f"/api/company/{company_id}/users", headers=headers)
    return {user["email"]: user for user in response.json()}


async def company_row(
    client: AsyncClient, headers: dict[str, str], name: str
) -> dict[str, Any]:
    response = await client.get(f"/api/companies?query={name}", headers=headers)
    return response.json()["items"][0]


async def listed_user(
    client: AsyncClient, headers: dict[str, str], email: str
) -> dict[str, Any]:
    response = await client.get(f"/api/users?query={email}", headers=headers)
    return response.json()["items"][0]


async def add_newcomer(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    staff_headers: dict[str, str],
    company_id: object,
) -> User:
    newcomer = await create_user(email=NEWCOMER_EMAIL, password=None)
    await client.post(
        f"/api/companies/{company_id}/members",
        json={"user_id": str(newcomer.id)},
        headers=staff_headers,
    )
    return newcomer


async def test_existing_members_are_not_new(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    listed = await members(client, staff_headers, company_user.company_id)

    assert listed[company_user.email]["new_in_company_since"] is None
    assert (await company_row(client, staff_headers, "Acme"))["new_members_count"] == 0


async def test_a_member_added_by_staff_is_new(
    client: AsyncClient,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
):
    await add_newcomer(client, create_user, staff_headers, company_user.company_id)

    listed = await members(client, staff_headers, company_user.company_id)
    assert listed[NEWCOMER_EMAIL]["new_in_company_since"] is not None
    assert listed[company_user.email]["new_in_company_since"] is None
    assert (await company_row(client, staff_headers, "Acme"))["new_members_count"] == 1
    assert (await listed_user(client, staff_headers, NEWCOMER_EMAIL))[
        "new_in_company_since"
    ] is not None
    own_members = await client.get("/api/company/me/users", headers=company_headers)
    assert all("new_in_company_since" not in user for user in own_members.json())


async def test_staff_mark_the_new_members_of_a_company_as_seen(
    client: AsyncClient,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    staff_headers: dict[str, str],
):
    await add_newcomer(client, create_user, staff_headers, company_user.company_id)

    response = await client.post(
        f"/api/companies/{company_user.company_id}/members/acknowledge",
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert all(user["new_in_company_since"] is None for user in response.json())
    listed = await members(client, staff_headers, company_user.company_id)
    assert listed[NEWCOMER_EMAIL]["new_in_company_since"] is None
    assert (await company_row(client, staff_headers, "Acme"))["new_members_count"] == 0


async def test_accepting_an_invite_makes_the_user_new(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    staff_headers: dict[str, str],
):
    assert company_user.company_id is not None
    await CompanyRepository(db_session).create_invite(
        INVITE_TOKEN,
        company_user.company_id,
        NEWCOMER_EMAIL,
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    newcomer = await create_user(email=NEWCOMER_EMAIL, password=None)

    accepted = await client.post(
        f"/api/company/invite/{INVITE_TOKEN}/accept",
        headers={**await auth_headers(newcomer), **csrf_headers},
    )

    assert accepted.status_code == 200
    listed = await members(client, staff_headers, company_user.company_id)
    assert listed[NEWCOMER_EMAIL]["new_in_company_since"] is not None


async def test_setting_up_a_company_makes_the_founder_new(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    staff_headers: dict[str, str],
):
    founder = await create_user(email=NEWCOMER_EMAIL, password=None)

    created = await client.post(
        "/api/company/setup",
        json={"name": "Gamma AG"},
        headers={**await auth_headers(founder), **csrf_headers},
    )

    assert created.status_code == 200
    assert (await company_row(client, staff_headers, "Gamma"))["new_members_count"] == 1


async def test_staff_reassignment_makes_the_user_new_and_removal_forgets_it(
    client: AsyncClient,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    staff_headers: dict[str, str],
):
    newcomer = await create_user(email=NEWCOMER_EMAIL, password=None)

    await client.patch(
        f"/api/users/{newcomer.id}",
        json={"company_id": str(company_user.company_id)},
        headers=staff_headers,
    )
    assert (await listed_user(client, staff_headers, NEWCOMER_EMAIL))[
        "new_in_company_since"
    ] is not None

    await client.delete(
        f"/api/companies/{company_user.company_id}/members/{newcomer.id}",
        headers=staff_headers,
    )
    assert (await listed_user(client, staff_headers, NEWCOMER_EMAIL))[
        "new_in_company_since"
    ] is None
