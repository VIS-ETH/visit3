import json
from collections.abc import AsyncIterator

from httpx import AsyncClient

from app.core.body_limit import DEFAULT_BODY_LIMIT_BYTES
from app.core.config import get_settings
from app.core.request_id import REQUEST_ID_HEADER
from tests.images import raster

OVERSIZED_NAME = "A" * DEFAULT_BODY_LIMIT_BYTES
CHUNK_BYTES = 64 * 1024


def oversized_json() -> bytes:
    return json.dumps({"name": OVERSIZED_NAME}).encode()


async def chunks(content: bytes) -> AsyncIterator[bytes]:
    for start in range(0, len(content), CHUNK_BYTES):
        yield content[start : start + CHUNK_BYTES]


async def test_an_oversized_json_body_is_rejected_before_it_is_read(
    client: AsyncClient, company_headers: dict[str, str]
):
    origin = get_settings().VISIT_FRONTEND_SERVER_URL

    response = await client.patch(
        "/api/company/me",
        content=oversized_json(),
        headers={
            **company_headers,
            "Content-Type": "application/json",
            "Origin": origin,
        },
    )

    assert response.status_code == 413
    assert response.json()["code"] == "error.storage_file_too_large"
    assert response.json()["requestId"] == response.headers[REQUEST_ID_HEADER]
    assert response.headers["access-control-allow-origin"] == origin


async def test_a_streamed_json_body_is_cut_off_at_the_limit(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.patch(
        "/api/company/me",
        content=chunks(oversized_json()),
        headers={**company_headers, "Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "error.storage_file_too_large"
    assert response.json()["requestId"] == response.headers[REQUEST_ID_HEADER]


async def test_an_unauthenticated_oversized_body_is_rejected(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        content=oversized_json(),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


async def test_an_upload_above_the_json_limit_passes_within_its_own_limit(
    client: AsyncClient, company_headers: dict[str, str]
):
    padding = b"\x00" * (2 * DEFAULT_BODY_LIMIT_BYTES)

    response = await client.post(
        "/api/company/me/profile/logo",
        files={"file": ("logo.png", raster(1, 1) + padding, "image/png")},
        headers=company_headers,
    )

    assert response.status_code == 200


async def test_a_small_json_body_passes(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.patch(
        "/api/company/me", json={"name": "Acme Robotics"}, headers=company_headers
    )

    assert response.status_code == 200
