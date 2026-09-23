from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.models.user import User

PHONE_NUMBER = "+41791234567"


@pytest.fixture
async def profile_headers(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    user = await create_user(
        email="profile@example.com",
        first_name="Ada",
        last_name="Lovelace",
        phone_number=PHONE_NUMBER,
    )
    return {**await auth_headers(user), **csrf_headers}


async def test_admin_email_change_unconfirms_email_and_sends_confirmation(
    client: AsyncClient,
    company_user: User,
    staff_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"email": "moved@example.com"},
        headers=staff_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "moved@example.com"
    assert body["email_confirmed"] is False
    mail_stub.SendMail.assert_awaited_once()


async def test_admin_email_change_to_existing_email_is_rejected(
    client: AsyncClient,
    company_user: User,
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
):
    other = await create_user(email="other@example.com")

    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"email": other.email},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.email_used"


async def test_admin_email_change_revokes_refresh_tokens(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    staff_headers: dict[str, str],
):
    login = await client.post(
        "/api/auth/login",
        data={"username": company_user.email, "password": "test-password-123"},
        headers=csrf_headers,
    )
    client.cookies.set("refresh_token", login.cookies["refresh_token"])

    await client.patch(
        f"/api/users/{company_user.id}",
        json={"email": "moved@example.com"},
        headers=staff_headers,
    )
    response = await client.post("/api/auth/refresh", headers=csrf_headers)

    assert response.status_code == 401


async def test_profile_update_clears_phone_number_sent_as_null(
    client: AsyncClient, profile_headers: dict[str, str]
):
    response = await client.patch(
        "/api/user/me",
        json={"phone_number": None},
        headers=profile_headers,
    )

    assert response.status_code == 200
    assert response.json()["phone_number"] is None


async def test_profile_update_keeps_omitted_phone_number(
    client: AsyncClient, profile_headers: dict[str, str]
):
    response = await client.patch(
        "/api/user/me",
        json={"first_name": "Grace"},
        headers=profile_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Grace"
    assert body["phone_number"] == PHONE_NUMBER


async def test_profile_update_clears_last_name_sent_as_null(
    client: AsyncClient, profile_headers: dict[str, str]
):
    response = await client.patch(
        "/api/user/me",
        json={"last_name": None},
        headers=profile_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["last_name"] is None
    assert body["first_name"] == "Ada"


async def test_admin_user_update_rejects_email_sent_as_null(
    client: AsyncClient,
    company_user: User,
    staff_headers: dict[str, str],
):
    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"email": None},
        headers=staff_headers,
    )

    assert response.status_code == 422
    assert response.json()["fieldErrors"][0]["field"] == "email"


async def test_confirmation_mail_is_rate_limited_per_user(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    limit = get_settings().RATE_LIMIT_MAX_REQUESTS
    user = await create_user(email="unconfirmed@example.com", email_confirmed=False)
    other = await create_user(email="other@example.com", email_confirmed=False)
    headers = {**await auth_headers(user), **csrf_headers}
    other_headers = {**await auth_headers(other), **csrf_headers}

    accepted = [
        (
            await client.post("/api/user/send-confirmation-email", headers=headers)
        ).status_code
        for _ in range(limit)
    ]
    blocked = await client.post("/api/user/send-confirmation-email", headers=headers)
    other_response = await client.post(
        "/api/user/send-confirmation-email", headers=other_headers
    )

    assert accepted == [200] * limit
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "error.rate_limited"
    assert other_response.status_code == 200


async def test_current_user_exposes_the_kp_president_flag(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    president = await create_user(
        email="president@example.com",
        is_staff=True,
        is_company=False,
        roles=[get_settings().VISIT_KP_PRESIDENT_ROLE],
    )
    headers = {**await auth_headers(president), **csrf_headers}

    response = await client.get("/api/user/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["is_kp_president"] is True


async def test_plain_staff_is_not_flagged_as_kp_president(
    client: AsyncClient,
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    headers = {**await auth_headers(staff_user), **csrf_headers}

    response = await client.get("/api/user/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["is_kp_president"] is False


async def test_admin_is_flagged_as_kp_president(
    client: AsyncClient, admin_user: User, staff_headers: dict[str, str]
):
    response = await client.get("/api/user/me", headers=staff_headers)

    assert response.status_code == 200
    assert response.json()["is_kp_president"] is True


async def test_listed_staff_carry_the_kp_president_flag(
    client: AsyncClient,
    staff_user: User,
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
):
    await create_user(
        email="president@example.com",
        is_staff=True,
        is_company=False,
        roles=[get_settings().VISIT_KP_PRESIDENT_ROLE],
    )

    response = await client.get("/api/user/staff", headers=staff_headers)

    assert response.status_code == 200
    flags = {entry["email"]: entry["is_kp_president"] for entry in response.json()}
    assert flags["president@example.com"] is True
    assert flags[staff_user.email] is False
