from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.models.user import User
from tests.api.conftest import company_profile_payload


async def test_moving_the_kp_contact_to_another_company_clears_the_contact(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
):
    saved = await client.put(
        "/api/company/me/profile",
        json=company_profile_payload(kp_contact_user_id=str(company_user.id)),
        headers=company_headers,
    )
    assert saved.status_code == 200, saved.text
    await create_user(email="second@example.com", company_name=None)
    other = await create_user(email="other@example.com", company_name="Other AG")

    moved = await client.patch(
        f"/api/users/{company_user.id}",
        json={"company_id": str(other.company_id)},
        headers=staff_headers,
    )

    assert moved.status_code == 200, moved.text
    profile = await client.get(
        f"/api/company/{company_user.company_id}/profile", headers=staff_headers
    )
    assert profile.json()["kp_contact_user_id"] is None
    assert profile.json()["profile_complete"] is False


async def test_confirming_a_company_renamed_since_the_review_is_a_conflict(
    client: AsyncClient,
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    owner = await create_user(
        email="owner@example.com", company_name="Legit AG", company_confirmed=False
    )
    company_id = owner.company_id
    renamed = await client.patch(
        "/api/company/me",
        json={"name": "Totally Different"},
        headers={**await auth_headers(owner), **csrf_headers},
    )
    assert renamed.status_code == 200, renamed.text

    confirmed = await client.post(
        f"/api/companies/{company_id}/confirm",
        json={"name": "Legit AG"},
        headers=staff_headers,
    )

    assert confirmed.status_code == 409
    assert confirmed.json()["code"] == "error.conflict"
    found = await client.get(
        "/api/companies", params={"query": "Totally Different"}, headers=staff_headers
    )
    assert [item["confirmed_at"] for item in found.json()["items"]] == [None]


async def test_an_unconfirmed_company_cannot_send_invites(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    owner = await create_user(
        email="owner@example.com",
        company_name="Verify your account at evil.example",
        company_confirmed=False,
    )

    response = await client.post(
        "/api/company/invite",
        json={"email": "victim@example.com"},
        headers={**await auth_headers(owner), **csrf_headers},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.company_not_confirmed"
    mail_stub.SendMail.assert_not_awaited()
