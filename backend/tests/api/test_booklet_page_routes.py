from base64 import b64decode
from collections.abc import Awaitable, Callable, Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core import deps
from app.core.config import get_settings
from app.models.user import User
from app.services.pdf_service import PdfService, RenderedImage
from tests.api.conftest import company_profile_payload

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MY_PAGE = "/api/company/me/profile/booklet-page"


def company_page(company_id: object) -> str:
    return f"/api/company/{company_id}/profile/booklet-page"


@pytest.fixture
def instant_pdf_service(api_app: FastAPI) -> Iterator[None]:
    service = AsyncMock(spec=PdfService)
    service.render_png.return_value = RenderedImage(png=PNG_SIGNATURE, metadata=False)
    api_app.dependency_overrides[deps.get_pdf_service] = lambda: service
    yield
    api_app.dependency_overrides.pop(deps.get_pdf_service, None)


async def preview_statuses(
    client: AsyncClient, url: str, headers: dict[str, str], count: int
) -> list[int]:
    return [
        (
            await client.post(url, json=company_profile_payload(), headers=headers)
        ).status_code
        for _ in range(count)
    ]


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


async def test_the_live_preview_is_rate_limited_per_user(
    client: AsyncClient,
    company_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    instant_pdf_service: None,
):
    limit = get_settings().BOOKLET_PAGE_RATE_LIMIT_MAX_REQUESTS
    other = await create_user(email="other@example.com", company_name="Other AG")
    other_headers = {**await auth_headers(other), **csrf_headers}

    accepted = await preview_statuses(client, MY_PAGE, company_headers, limit)
    blocked = await client.post(
        MY_PAGE, json=company_profile_payload(), headers=company_headers
    )
    other_response = await client.post(
        MY_PAGE, json=company_profile_payload(), headers=other_headers
    )

    assert accepted == [200] * limit
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "error.rate_limited"
    assert other_response.status_code == 200


async def test_the_staff_preview_is_rate_limited(
    client: AsyncClient,
    company_user: User,
    staff_headers: dict[str, str],
    instant_pdf_service: None,
):
    limit = get_settings().BOOKLET_PAGE_RATE_LIMIT_MAX_REQUESTS
    url = company_page(company_user.company_id)

    accepted = await preview_statuses(client, url, staff_headers, limit)
    blocked = await client.post(
        url, json=company_profile_payload(), headers=staff_headers
    )

    assert accepted == [200] * limit
    assert blocked.status_code == 429


def test_the_preview_limit_fits_a_debounced_live_preview():
    settings = get_settings()

    assert settings.BOOKLET_PAGE_RATE_LIMIT_MAX_REQUESTS == 60
    assert settings.BOOKLET_PAGE_RATE_LIMIT_WINDOW_SECONDS == 60
