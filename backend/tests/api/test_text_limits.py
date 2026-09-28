from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient, Response

from app.models.user import User
from app.schemas.text import (
    COMPANY_NAME_MAX_LENGTH,
    NAME_MAX_LENGTH,
    PROFILE_TEXT_LIMITS,
)
from tests.api.conftest import KpSetup


def text(length: int) -> str:
    return "a" * length


@pytest.mark.parametrize(("field", "limit"), sorted(PROFILE_TEXT_LIMITS.items()))
async def test_profile_text_fields_accept_their_limit_and_reject_more(
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    field: str,
    limit: int,
):
    at_limit = await complete_company_profile(company_headers, **{field: text(limit)})
    over_limit = await complete_company_profile(
        company_headers, **{field: text(limit + 1)}
    )

    assert at_limit.status_code == 200
    assert over_limit.status_code == 422
    assert over_limit.json()["fieldErrors"][0]["code"] == "validation.too_long"


async def test_the_company_name_is_limited(
    client: AsyncClient, company_headers: dict[str, str]
):
    at_limit = await client.patch(
        "/api/company/me",
        json={"name": text(COMPANY_NAME_MAX_LENGTH)},
        headers=company_headers,
    )
    over_limit = await client.patch(
        "/api/company/me",
        json={"name": text(COMPANY_NAME_MAX_LENGTH + 1)},
        headers=company_headers,
    )

    assert at_limit.status_code == 200
    assert over_limit.status_code == 422


async def test_company_setup_limits_the_name(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    user = await create_user(email="founder@example.com")
    headers = {**await auth_headers(user), **csrf_headers}

    response = await client.post(
        "/api/company/setup",
        json={"name": text(COMPANY_NAME_MAX_LENGTH + 1)},
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "limit"),
    [("first_name", NAME_MAX_LENGTH), ("last_name", NAME_MAX_LENGTH)],
)
async def test_user_profile_fields_are_limited(
    client: AsyncClient, company_headers: dict[str, str], field: str, limit: int
):
    response = await client.patch(
        "/api/user/me", json={field: text(limit + 1)}, headers=company_headers
    )

    assert response.status_code == 422


async def test_registration_limits_the_names(
    client: AsyncClient, csrf_headers: dict[str, str]
):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "new@example.com",
            "password": "a-long-enough-password-1",
            "first_name": text(NAME_MAX_LENGTH + 1),
            "last_name": "Lovelace",
        },
        headers=csrf_headers,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["first_name", "last_name", "position"])
async def test_nametag_fields_are_limited(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
    field: str,
):
    booking_id = (await register_booking(company_headers, kp_setup)).json()["id"]
    name_tag = {"first_name": "Ada", "last_name": "Lovelace", "position": "Engineer"}

    at_limit = await client.put(
        f"/api/kp/bookings/{booking_id}/nametags",
        json={"name_tags": [{**name_tag, field: text(NAME_MAX_LENGTH)}]},
        headers=company_headers,
    )
    over_limit = await client.put(
        f"/api/kp/bookings/{booking_id}/nametags",
        json={"name_tags": [{**name_tag, field: text(NAME_MAX_LENGTH + 1)}]},
        headers=company_headers,
    )

    assert at_limit.status_code == 200
    assert over_limit.status_code == 422
