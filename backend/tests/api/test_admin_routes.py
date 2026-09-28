from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.api.conftest import KpSetup, move_event_into_the_past

IMPERSONATE_HEADER = "X-Impersonate-User-Id"
UNCONFIRMED_EMAIL = "pending@example.com"
OTHER_COMPANY_NAME = "Beta GmbH"
OTHER_COMPANY_EMAIL = "beta@example.com"


@pytest.fixture
async def unconfirmed_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email=UNCONFIRMED_EMAIL,
        password=None,
        company_name="Pending AG",
        user_confirmed=False,
    )


@pytest.fixture
async def non_admin_staff_headers(
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(staff_user), **csrf_headers}


async def company_members(
    client: AsyncClient, company_id: str, headers: dict[str, str]
) -> list[str]:
    response = await client.get(f"/api/company/{company_id}/users", headers=headers)
    return [user["email"] for user in response.json()]


async def test_unconfirmed_users_are_listed_until_they_are_confirmed(
    client: AsyncClient, unconfirmed_user: User, staff_headers: dict[str, str]
):
    pending = await client.get("/api/user/unconfirmed", headers=staff_headers)
    confirmed = await client.post(
        f"/api/users/{unconfirmed_user.id}/confirm", headers=staff_headers
    )
    remaining = await client.get("/api/user/unconfirmed", headers=staff_headers)

    assert [user["email"] for user in pending.json()] == [UNCONFIRMED_EMAIL]
    assert confirmed.status_code == 200
    assert confirmed.json()["user_confirmed"] is True
    assert remaining.json() == []


async def test_confirming_an_unknown_user_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.post(f"/api/users/{uuid4()}/confirm", headers=staff_headers)

    assert response.status_code == 404
    assert response.json()["code"] == "error.user_not_found"


async def test_admin_updates_a_company_user(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"first_name": "Grace", "phone_number": "+41791234567"},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Grace"
    assert response.json()["phone_number"] == "+41791234567"


async def test_admin_user_update_rejects_an_invalid_phone_number(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"phone_number": "not-a-number"},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.phone_number_invalid"


async def test_admin_deletes_a_company_user(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.delete(
        f"/api/users/{company_user.id}", headers=staff_headers
    )
    remaining = await client.get("/api/user/companies", headers=staff_headers)

    assert response.status_code == 200
    assert [user["email"] for user in remaining.json()] == []


@pytest.mark.parametrize("target", ["staff", "admin"])
async def test_staff_cannot_delete_privileged_users(
    client: AsyncClient,
    staff_user: User,
    admin_user: User,
    non_admin_staff_headers: dict[str, str],
    target: str,
):
    user = staff_user if target == "staff" else admin_user

    response = await client.delete(
        f"/api/users/{user.id}", headers=non_admin_staff_headers
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_admin_deletes_a_staff_user(
    client: AsyncClient, staff_user: User, staff_headers: dict[str, str]
):
    response = await client.delete(f"/api/users/{staff_user.id}", headers=staff_headers)
    remaining = await client.get("/api/user/staff", headers=staff_headers)

    assert response.status_code == 200
    assert staff_user.email not in [user["email"] for user in remaining.json()]


async def test_deleting_yourself_is_refused(
    client: AsyncClient, admin_user: User, staff_headers: dict[str, str]
):
    response = await client.delete(f"/api/users/{admin_user.id}", headers=staff_headers)

    assert response.status_code == 403
    assert response.json()["identifier"].startswith("delete_user:self")


async def test_deleting_an_unknown_user_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.delete(f"/api/users/{uuid4()}", headers=staff_headers)

    assert response.status_code == 404
    assert response.json()["code"] == "error.user_not_found"


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
async def test_staff_without_admin_manages_company_users(
    client: AsyncClient,
    company_user: User,
    non_admin_staff_headers: dict[str, str],
    method: str,
):
    response = await client.request(
        method,
        f"/api/users/{company_user.id}",
        json={"first_name": "Grace"} if method == "PATCH" else None,
        headers=non_admin_staff_headers,
    )

    assert response.status_code == 200


@pytest.mark.parametrize("flag", ["is_staff", "is_admin"])
async def test_staff_without_admin_cannot_change_privilege_flags(
    client: AsyncClient,
    company_user: User,
    non_admin_staff_headers: dict[str, str],
    flag: str,
):
    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={flag: True},
        headers=non_admin_staff_headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_admin_grants_staff_rights(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"is_staff": True},
        headers=staff_headers,
    )
    listed = await client.get("/api/user/staff", headers=staff_headers)

    assert response.status_code == 200
    assert company_user.email in [user["email"] for user in listed.json()]


async def test_admin_can_impersonate_a_company_user(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.get(
        "/api/user/me",
        headers={**staff_headers, IMPERSONATE_HEADER: str(company_user.id)},
    )

    assert response.status_code == 200
    assert response.json()["email"] == company_user.email


async def test_staff_without_admin_cannot_impersonate(
    client: AsyncClient, company_user: User, non_admin_staff_headers: dict[str, str]
):
    response = await client.get(
        "/api/user/me",
        headers={**non_admin_staff_headers, IMPERSONATE_HEADER: str(company_user.id)},
    )

    assert response.status_code == 403
    assert response.json()["identifier"].startswith("impersonate:not_admin")


@pytest.mark.parametrize(
    ("target", "identifier"),
    [("not-a-uuid", "impersonate:invalid_uuid"), (None, "impersonate:user_not_found")],
)
async def test_impersonation_of_an_unusable_target_is_refused(
    client: AsyncClient, staff_headers: dict[str, str], target: str, identifier: str
):
    response = await client.get(
        "/api/user/me",
        headers={**staff_headers, IMPERSONATE_HEADER: target or str(uuid4())},
    )

    assert response.status_code == 403
    assert response.json()["identifier"].startswith(identifier)


async def test_company_list_reports_user_counts(
    client: AsyncClient,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    staff_headers: dict[str, str],
):
    await create_user(
        email=OTHER_COMPANY_EMAIL, password=None, company_name=OTHER_COMPANY_NAME
    )

    response = await client.get(
        "/api/company/management/companies", headers=staff_headers
    )

    counts = {company["name"]: company["users_count"] for company in response.json()}
    assert response.status_code == 200
    assert counts == {"Acme AG": 1, OTHER_COMPANY_NAME: 1}


async def test_company_with_users_lists_the_members(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.get(
        f"/api/company/{company_user.company_id}/with-users", headers=staff_headers
    )

    body = response.json()
    assert response.status_code == 200
    assert body["name"] == "Acme AG"
    assert [user["email"] for user in body["users"]] == [company_user.email]


@pytest.mark.parametrize("suffix", ["users", "with-users"])
async def test_reading_an_unknown_company_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str], suffix: str
):
    response = await client.get(
        f"/api/company/{uuid4()}/{suffix}", headers=staff_headers
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.company_not_found"


@pytest.mark.parametrize("mode", ["delete-with-users", "delete-keep-users"])
async def test_company_deletion_is_refused_while_upcoming_bookings_exist(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
    mode: str,
):
    await register_booking(company_headers, kp_setup)

    response = await client.delete(
        f"/api/company/{company_user.company_id}/{mode}", headers=staff_headers
    )
    members = await company_members(client, str(company_user.company_id), staff_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "error.company_has_upcoming_bookings"
    assert members == [company_user.email]


async def test_company_deletion_keeps_users_after_the_event_has_passed(
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

    response = await client.delete(
        f"/api/company/{company_user.company_id}/delete-keep-users",
        headers=staff_headers,
    )
    companies = await client.get(
        "/api/company/management/companies", headers=staff_headers
    )
    users = await client.get("/api/user/companies", headers=staff_headers)

    assert response.status_code == 200
    assert companies.json() == []
    assert [(user["email"], user["company"]) for user in users.json()] == [
        (company_user.email, None)
    ]


async def test_company_deletion_removes_users_after_the_event_has_passed(
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

    response = await client.delete(
        f"/api/company/{company_user.company_id}/delete-with-users",
        headers=staff_headers,
    )
    users = await client.get("/api/user/companies", headers=staff_headers)

    assert response.status_code == 200
    assert users.json() == []


@pytest.mark.parametrize("mode", ["delete-with-users", "delete-keep-users"])
async def test_staff_without_admin_cannot_delete_a_company(
    client: AsyncClient,
    company_user: User,
    non_admin_staff_headers: dict[str, str],
    mode: str,
):
    response = await client.delete(
        f"/api/company/{company_user.company_id}/{mode}",
        headers=non_admin_staff_headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_removing_a_company_user_detaches_the_user(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    company_id = str(company_user.company_id)

    response = await client.delete(
        f"/api/companies/{company_id}/members/{company_user.id}", headers=staff_headers
    )
    members = await company_members(client, company_id, staff_headers)
    users = await client.get("/api/user/companies", headers=staff_headers)

    assert response.status_code == 200
    assert members == []
    assert [(user["email"], user["company"]) for user in users.json()] == [
        (company_user.email, None)
    ]


async def test_removing_a_user_of_another_company_is_rejected(
    client: AsyncClient,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    staff_headers: dict[str, str],
):
    other = await create_user(
        email=OTHER_COMPANY_EMAIL, password=None, company_name=OTHER_COMPANY_NAME
    )

    response = await client.delete(
        f"/api/companies/{company_user.company_id}/members/{other.id}",
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.company_user_not_found"


async def test_removing_an_unknown_company_user_is_not_found(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.delete(
        f"/api/companies/{company_user.company_id}/members/{uuid4()}",
        headers=staff_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.user_not_found"


async def test_staff_without_admin_removes_a_company_user(
    client: AsyncClient, company_user: User, non_admin_staff_headers: dict[str, str]
):
    response = await client.delete(
        f"/api/companies/{company_user.company_id}/members/{company_user.id}",
        headers=non_admin_staff_headers,
    )

    assert response.status_code == 200
