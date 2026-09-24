from base64 import b64decode

from httpx import AsyncClient

from app.models.user import User
from tests.api.conftest import company_profile_payload

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MY_PAGE = "/api/company/me/profile/booklet-page"


def company_page(company_id: object) -> str:
    return f"/api/company/{company_id}/profile/booklet-page"


async def test_company_previews_its_booklet_page(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.post(
        MY_PAGE, json=company_profile_payload(), headers=company_headers
    )

    assert response.status_code == 200
    assert b64decode(response.json()["png_base64"]).startswith(PNG_SIGNATURE)
    assert response.json()["overflow"] is False


async def test_the_preview_does_not_save_the_form_values(
    client: AsyncClient, company_headers: dict[str, str]
):
    await client.post(
        MY_PAGE,
        json=company_profile_payload(brand_name="Unsaved Labs"),
        headers=company_headers,
    )
    profile = await client.get("/api/company/me/profile", headers=company_headers)

    assert profile.json()["id"] is None
    assert profile.json()["brand_name"] == ""


async def test_the_preview_flags_a_description_that_overflows_the_page(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.post(
        MY_PAGE,
        json=company_profile_payload(description="Zeile\n" * 400),
        headers=company_headers,
    )

    assert response.status_code == 200
    assert response.json()["overflow"] is True


async def test_the_preview_rejects_a_description_over_the_limit(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.post(
        MY_PAGE,
        json=company_profile_payload(description="x" * 2501),
        headers=company_headers,
    )

    assert response.status_code == 422


async def test_staff_previews_the_page_of_any_company(
    client: AsyncClient, company_user: User, staff_headers: dict[str, str]
):
    response = await client.post(
        company_page(company_user.company_id),
        json=company_profile_payload(),
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert b64decode(response.json()["png_base64"]).startswith(PNG_SIGNATURE)


async def test_staff_preview_of_an_unknown_company_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.post(
        company_page("3fa85f64-5717-4562-b3fc-2c963f66afa6"),
        json=company_profile_payload(),
        headers=staff_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.company_not_found"
