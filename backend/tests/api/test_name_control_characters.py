import pytest
from httpx import AsyncClient

INJECTED_NAMES = ["Acme\r\nBcc: victim@example.com", "Acme\tAG", "Acme\x00AG"]


@pytest.mark.parametrize("name", INJECTED_NAMES)
async def test_a_company_name_with_control_characters_is_rejected(
    client: AsyncClient, company_headers: dict[str, str], name: str
):
    response = await client.patch(
        "/api/company/me", json={"name": name}, headers=company_headers
    )

    assert response.status_code == 422


@pytest.mark.parametrize("name", INJECTED_NAMES)
async def test_a_staff_rename_with_control_characters_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: object,
    name: str,
):
    companies = await client.get("/api/companies", headers=staff_headers)
    company_id = companies.json()["items"][0]["id"]

    response = await client.patch(
        f"/api/companies/{company_id}", json={"name": name}, headers=staff_headers
    )

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["first_name", "last_name"])
async def test_a_user_name_with_control_characters_is_rejected(
    client: AsyncClient, company_headers: dict[str, str], field: str
):
    response = await client.patch(
        "/api/user/me",
        json={field: "Ada\r\nBcc: victim@example.com"},
        headers=company_headers,
    )

    assert response.status_code == 422


async def test_registration_with_control_characters_in_a_name_is_rejected(
    client: AsyncClient, csrf_headers: dict[str, str]
):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "new@example.com",
            "password": "a-long-enough-password-1",
            "first_name": "Ada\nBcc: victim@example.com",
            "last_name": "Lovelace",
        },
        headers=csrf_headers,
    )

    assert response.status_code == 422


async def test_a_brand_name_with_control_characters_is_rejected(
    client: AsyncClient, company_headers: dict[str, str], complete_company_profile
):
    response = await complete_company_profile(
        company_headers, brand_name="Acme\r\nBcc: victim@example.com"
    )

    assert response.status_code == 422


async def test_names_are_still_trimmed(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.patch(
        "/api/company/me", json={"name": "  Acme Robotics\n"}, headers=company_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Acme Robotics"
