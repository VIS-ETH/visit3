from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

from app.models.user import User

ZERO_WIDTH_SPACE = "​"
BRAILLE_BLANK = "⠀"
NO_BREAK_SPACE = "\xa0"


async def set_up_company(
    client: AsyncClient,
    headers: dict[str, str],
    name: str,
):
    return await client.post("/api/company/setup", json={"name": name}, headers=headers)


@pytest.fixture
def founder_headers(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> Callable[[str], Awaitable[dict[str, str]]]:
    async def _founder_headers(email: str) -> dict[str, str]:
        user = await create_user(email=email)
        return {**await auth_headers(user), **csrf_headers}

    return _founder_headers


@pytest.mark.parametrize(
    "twin", ["ACME AG", "acme ag", f"Acme{NO_BREAK_SPACE}AG", "Ａｃｍｅ AG"]
)
async def test_a_company_name_differing_only_in_case_or_width_is_taken(
    client: AsyncClient,
    founder_headers: Callable[[str], Awaitable[dict[str, str]]],
    twin: str,
):
    first = await set_up_company(
        client, await founder_headers("first@example.com"), "Acme AG"
    )
    assert first.status_code == 200, first.text

    second = await set_up_company(
        client, await founder_headers("second@example.com"), twin
    )

    assert second.status_code == 409, second.text


@pytest.mark.parametrize(
    "name", [ZERO_WIDTH_SPACE, f"Acme{ZERO_WIDTH_SPACE} AG", BRAILLE_BLANK]
)
async def test_a_company_name_with_invisible_characters_is_rejected(
    client: AsyncClient,
    founder_headers: Callable[[str], Awaitable[dict[str, str]]],
    name: str,
):
    response = await set_up_company(
        client, await founder_headers("founder@example.com"), name
    )

    assert response.status_code == 422, response.text


@pytest.mark.parametrize("name", [ZERO_WIDTH_SPACE, BRAILLE_BLANK])
async def test_a_person_name_of_invisible_characters_is_rejected(
    client: AsyncClient, company_headers: dict[str, str], name: str
):
    response = await client.patch(
        "/api/user/me", json={"first_name": name}, headers=company_headers
    )

    assert response.status_code == 422, response.text


async def test_a_person_name_cannot_be_cleared_with_null(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.patch(
        "/api/user/me",
        json={"first_name": None, "last_name": None},
        headers=company_headers,
    )

    assert response.status_code == 422, response.text
    me = await client.get("/api/user/me", headers=company_headers)
    assert me.json()["first_name"] == "Test"
