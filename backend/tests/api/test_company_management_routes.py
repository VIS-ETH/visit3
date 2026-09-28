from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response

from app.models.user import User
from tests.api.conftest import KpSetup

OTHER_COMPANY_NAME = "Beta GmbH"
OTHER_COMPANY_EMAIL = "beta@example.com"


@pytest.fixture
async def non_admin_staff_headers(
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(staff_user), **csrf_headers}


@pytest.fixture
async def other_company_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email=OTHER_COMPANY_EMAIL, password=None, company_name=OTHER_COMPANY_NAME
    )


async def test_company_page_reports_members_and_bookings(
    client: AsyncClient,
    company_user: User,
    other_company_user: User,
    company_headers: dict[str, str],
    non_admin_staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    response = await client.get("/api/companies", headers=non_admin_staff_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [
        (item["name"], item["users_count"], item["bookings_count"])
        for item in body["items"]
    ] == [("Acme AG", 1, 1), (OTHER_COMPANY_NAME, 1, 0)]


async def test_company_page_is_paginated(
    client: AsyncClient,
    company_user: User,
    other_company_user: User,
    staff_headers: dict[str, str],
):
    response = await client.get(
        "/api/companies?page=2&page_size=1", headers=staff_headers
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["name"] for item in response.json()["items"]] == [OTHER_COMPANY_NAME]


async def test_company_page_searches_by_name(
    client: AsyncClient,
    company_user: User,
    other_company_user: User,
    staff_headers: dict[str, str],
):
    response = await client.get("/api/companies?query=beta", headers=staff_headers)

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == [OTHER_COMPANY_NAME]


async def test_staff_renames_a_company(
    client: AsyncClient, company_user: User, non_admin_staff_headers: dict[str, str]
):
    response = await client.patch(
        f"/api/companies/{company_user.company_id}",
        json={"name": "  Acme Holding  "},
        headers=non_admin_staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Acme Holding"
    assert set(response.json()) == {"id", "name"}


async def test_renaming_to_a_taken_name_is_refused(
    client: AsyncClient,
    company_user: User,
    other_company_user: User,
    staff_headers: dict[str, str],
):
    response = await client.patch(
        f"/api/companies/{company_user.company_id}",
        json={"name": OTHER_COMPANY_NAME},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.company_name_taken"


async def test_renaming_an_unknown_company_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.patch(
        f"/api/companies/{uuid4()}", json={"name": "Ghost AG"}, headers=staff_headers
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.company_not_found"


async def test_staff_adds_a_member_without_a_company(
    client: AsyncClient,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    non_admin_staff_headers: dict[str, str],
):
    newcomer = await create_user(email="newcomer@example.com", password=None)

    response = await client.post(
        f"/api/companies/{company_user.company_id}/members",
        json={"user_id": str(newcomer.id)},
        headers=non_admin_staff_headers,
    )
    members = await client.get(
        f"/api/company/{company_user.company_id}/users",
        headers=non_admin_staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["company"]["name"] == "Acme AG"
    assert sorted(user["email"] for user in members.json()) == [
        company_user.email,
        newcomer.email,
    ]


async def test_adding_a_member_of_another_company_is_refused(
    client: AsyncClient,
    company_user: User,
    other_company_user: User,
    staff_headers: dict[str, str],
):
    response = await client.post(
        f"/api/companies/{company_user.company_id}/members",
        json={"user_id": str(other_company_user.id)},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.user_already_in_company"


async def test_adding_a_staff_member_is_refused(
    client: AsyncClient,
    company_user: User,
    staff_user: User,
    staff_headers: dict[str, str],
):
    response = await client.post(
        f"/api/companies/{company_user.company_id}/members",
        json={"user_id": str(staff_user.id)},
        headers=staff_headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_adding_an_unknown_user_is_not_found(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.post(
        f"/api/companies/{company_user.company_id}/members",
        json={"user_id": str(uuid4())},
        headers=staff_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.user_not_found"


async def test_adding_a_member_to_an_unknown_company_is_not_found(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    staff_headers: dict[str, str],
):
    newcomer = await create_user(email="newcomer@example.com", password=None)

    response = await client.post(
        f"/api/companies/{uuid4()}/members",
        json={"user_id": str(newcomer.id)},
        headers=staff_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.company_not_found"


async def test_removing_the_last_booked_member_is_refused(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    response = await client.delete(
        f"/api/companies/{company_user.company_id}/members/{company_user.id}",
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.user_last_company_member"


async def test_removing_a_member_of_a_booked_company_keeps_the_last_one(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)
    colleague = await create_user(email="colleague@example.com", password=None)
    await client.post(
        f"/api/companies/{company_user.company_id}/members",
        json={"user_id": str(colleague.id)},
        headers=staff_headers,
    )

    response = await client.delete(
        f"/api/companies/{company_user.company_id}/members/{colleague.id}",
        headers=staff_headers,
    )

    assert response.status_code == 200
