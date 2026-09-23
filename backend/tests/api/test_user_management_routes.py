from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response

from app.core.config import get_settings
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
async def population(
    company_user: User,
    staff_user: User,
    create_user: Callable[..., Awaitable[User]],
) -> list[User]:
    pending = await create_user(
        email="pending@example.com",
        password=None,
        first_name="Grace",
        last_name="Hopper",
        user_confirmed=False,
    )
    other = await create_user(
        email=OTHER_COMPANY_EMAIL, password=None, company_name=OTHER_COMPANY_NAME
    )
    return [company_user, staff_user, pending, other]


async def emails(response: Response) -> list[str]:
    return [item["email"] for item in response.json()["items"]]


async def test_user_list_is_paginated_and_sorted_by_email(
    client: AsyncClient, population: list[User], staff_headers: dict[str, str]
):
    first = await client.get("/api/users?page=1&page_size=2", headers=staff_headers)
    second = await client.get("/api/users?page=2&page_size=2", headers=staff_headers)

    assert first.status_code == 200
    assert first.json()["total"] == 5
    assert first.json()["page"] == 1
    assert first.json()["page_size"] == 2
    assert await emails(first) == ["admin@example.com", OTHER_COMPANY_EMAIL]
    assert await emails(second) == ["company@example.com", "pending@example.com"]


async def test_user_list_rejects_an_oversized_page(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.get("/api/users?page_size=101", headers=staff_headers)

    assert response.status_code == 422
    assert response.json()["fieldErrors"][0]["field"] == "page_size"


@pytest.mark.parametrize(
    ("user_filter", "expected"),
    [
        ("unconfirmed", ["pending@example.com"]),
        (
            "company",
            [
                OTHER_COMPANY_EMAIL,
                "company@example.com",
                "pending@example.com",
            ],
        ),
        ("staff", ["admin@example.com", "staff@example.com"]),
    ],
)
async def test_user_list_filters_by_role_and_confirmation(
    client: AsyncClient,
    population: list[User],
    staff_headers: dict[str, str],
    user_filter: str,
    expected: list[str],
):
    response = await client.get(
        f"/api/users?filter={user_filter}", headers=staff_headers
    )

    assert response.status_code == 200
    assert await emails(response) == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("pending@", ["pending@example.com"]),
        ("hopper", ["pending@example.com"]),
        ("GRACE", ["pending@example.com"]),
        ("acme", ["company@example.com"]),
        ("beta gmbh", [OTHER_COMPANY_EMAIL]),
        ("nothing-matches", []),
    ],
)
async def test_user_search_covers_email_name_and_company(
    client: AsyncClient,
    population: list[User],
    staff_headers: dict[str, str],
    query: str,
    expected: list[str],
):
    response = await client.get(f"/api/users?query={query}", headers=staff_headers)

    assert response.status_code == 200
    assert await emails(response) == expected
    assert response.json()["total"] == len(expected)


async def test_user_list_carries_the_company_of_each_user(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.get("/api/users?query=acme", headers=staff_headers)

    assert response.status_code == 200
    assert response.json()["items"][0]["company"]["name"] == "Acme AG"


async def test_single_user_is_readable_by_staff(
    client: AsyncClient, company_user: User, non_admin_staff_headers: dict[str, str]
):
    response = await client.get(
        f"/api/users/{company_user.id}", headers=non_admin_staff_headers
    )

    assert response.status_code == 200
    assert response.json()["email"] == company_user.email
    assert response.json()["company"]["name"] == "Acme AG"


async def test_reading_an_unknown_user_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.get(f"/api/users/{uuid4()}", headers=staff_headers)

    assert response.status_code == 404
    assert response.json()["code"] == "error.user_not_found"


async def test_staff_resends_the_confirmation_mail(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    non_admin_staff_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    user = await create_user(
        email="unconfirmed@example.com", password=None, email_confirmed=False
    )

    response = await client.post(
        f"/api/users/{user.id}/resend-confirmation", headers=non_admin_staff_headers
    )

    assert response.status_code == 200
    mail_stub.SendMail.assert_awaited_once()


async def test_resending_for_an_unknown_user_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.post(
        f"/api/users/{uuid4()}/resend-confirmation", headers=staff_headers
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.user_not_found"


async def test_staff_resend_is_rate_limited(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    staff_headers: dict[str, str],
):
    limit = get_settings().RATE_LIMIT_MAX_REQUESTS
    user = await create_user(
        email="unconfirmed@example.com", password=None, email_confirmed=False
    )
    url = f"/api/users/{user.id}/resend-confirmation"

    accepted = [
        (await client.post(url, headers=staff_headers)).status_code
        for _ in range(limit)
    ]
    blocked = await client.post(url, headers=staff_headers)

    assert accepted == [200] * limit
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "error.rate_limited"


async def test_staff_confirms_a_user_through_the_patch_route(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    non_admin_staff_headers: dict[str, str],
):
    user = await create_user(
        email="pending@example.com", password=None, user_confirmed=False
    )

    response = await client.patch(
        f"/api/users/{user.id}",
        json={"user_confirmed": True},
        headers=non_admin_staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["user_confirmed"] is True


async def test_staff_reassigns_a_user_to_another_company(
    client: AsyncClient,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    non_admin_staff_headers: dict[str, str],
):
    other = await create_user(
        email=OTHER_COMPANY_EMAIL, password=None, company_name=OTHER_COMPANY_NAME
    )

    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"company_id": str(other.company_id)},
        headers=non_admin_staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["company"]["name"] == OTHER_COMPANY_NAME


async def test_staff_cannot_update_a_privileged_user(
    client: AsyncClient,
    admin_user: User,
    non_admin_staff_headers: dict[str, str],
):
    response = await client.patch(
        f"/api/users/{admin_user.id}",
        json={"email": "hijacked@example.com"},
        headers=non_admin_staff_headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_admin_updates_a_privileged_user(
    client: AsyncClient,
    staff_user: User,
    staff_headers: dict[str, str],
):
    response = await client.patch(
        f"/api/users/{staff_user.id}",
        json={"email": "new-staff@example.com"},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["email"] == "new-staff@example.com"


async def test_reassigning_to_an_unknown_company_is_not_found(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"company_id": str(uuid4())},
        headers=staff_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.company_not_found"


async def test_deleting_the_last_booked_company_member_is_refused(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    response = await client.delete(
        f"/api/users/{company_user.id}", headers=staff_headers
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.user_last_company_member"


async def test_detaching_the_last_booked_company_member_is_refused(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"company_id": None},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.user_last_company_member"


async def test_deleting_a_booked_company_member_keeps_the_others(
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

    response = await client.delete(f"/api/users/{colleague.id}", headers=staff_headers)

    assert response.status_code == 200
