from io import BytesIO

import pytest
from httpx import AsyncClient, Response
from PIL import Image

from app.core.config import get_settings
from app.services.event_banner_service import (
    BANNER_MAX_BYTES,
    BANNER_MIN_WIDTH,
    BANNER_WIDTHS,
)
from app.services.storage_service import StorageService
from tests.api.conftest import KpSetup, kp_payload
from tests.api.test_upload_routes import FakeS3Client
from tests.booklet_pdfs import make_pdf
from tests.images import decompression_bomb, raster

WEBP_SIGNATURE = b"WEBP"


def banner_url(event_id: str) -> str:
    return f"/api/kp/events/{event_id}/banner"


async def upload(
    client: AsyncClient,
    headers: dict[str, str],
    event_id: str,
    content: bytes,
    filename: str = "banner.png",
    content_type: str = "image/png",
) -> Response:
    return await client.put(
        banner_url(event_id),
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


def decoded_size(content: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(content)) as image:
        return image.size


@pytest.fixture
def s3_client() -> FakeS3Client:
    return FakeS3Client()


@pytest.fixture
def storage_service(s3_client: FakeS3Client) -> StorageService:
    service = StorageService.__new__(StorageService)
    service.settings = get_settings().model_copy(
        update={"S3_PUBLIC_ENDPOINT_URL": None}
    )
    service.client = s3_client
    return service


async def test_an_event_without_a_banner_has_none(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.get(banner_url(kp_setup.event_id), headers=staff_headers)

    assert response.status_code == 200
    assert response.json() is None


async def test_the_upload_stores_three_webp_widths(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
):
    response = await upload(
        client, staff_headers, kp_setup.event_id, raster(3200, 1000)
    )

    assert response.status_code == 200
    banner = response.json()
    assert (banner["width"], banner["height"]) == (2000, 625)
    assert [source["width"] for source in banner["sources"]] == list(BANNER_WIDTHS)
    stored = list(s3_client.objects.values())
    assert len(stored) == len(BANNER_WIDTHS)
    assert all(content_type == "image/webp" for _, content_type in stored)
    assert all(content[8:12] == WEBP_SIGNATURE for content, _ in stored)
    assert sorted(decoded_size(content) for content, _ in stored) == [
        (800, 250),
        (1200, 375),
        (2000, 625),
    ]
    assert all(
        source["url"].startswith("https://storage.test/kp/events/")
        for source in banner["sources"]
    )


async def test_a_narrow_upload_is_not_scaled_up(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
):
    response = await upload(client, staff_headers, kp_setup.event_id, raster(1000, 400))

    banner = response.json()
    assert (banner["width"], banner["height"]) == (1000, 400)
    assert [source["width"] for source in banner["sources"]] == [800, 1000]
    assert len(s3_client.objects) == 2


@pytest.mark.parametrize(
    ("content", "filename", "content_type"),
    [
        (raster(1600, 500, "GIF"), "banner.gif", "image/gif"),
        (make_pdf(), "banner.pdf", "application/pdf"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", "banner.svg", "image/svg+xml"),
    ],
    ids=["gif", "pdf", "svg"],
)
async def test_the_upload_rejects_other_file_types(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
    content: bytes,
    filename: str,
    content_type: str,
):
    response = await upload(
        client, staff_headers, kp_setup.event_id, content, filename, content_type
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.storage_file_invalid_mime_type"
    assert s3_client.objects == {}


async def test_the_upload_rejects_a_pixel_bomb(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
):
    response = await upload(
        client, staff_headers, kp_setup.event_id, decompression_bomb(30_000)
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.storage_image_too_large"
    assert s3_client.objects == {}


async def test_the_upload_rejects_a_file_over_the_banner_limit(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
):
    oversized = raster(1600, 500) + b"\x00" * BANNER_MAX_BYTES

    response = await upload(client, staff_headers, kp_setup.event_id, oversized)

    assert response.status_code in (400, 413)
    assert response.json()["code"] == "error.storage_file_too_large"
    assert s3_client.objects == {}


async def test_the_upload_rejects_an_image_narrower_than_the_card(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
):
    response = await upload(
        client, staff_headers, kp_setup.event_id, raster(BANNER_MIN_WIDTH - 1, 200)
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.event_banner_too_small"
    assert s3_client.objects == {}


async def test_a_new_upload_replaces_the_previous_banner(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
):
    first = await upload(client, staff_headers, kp_setup.event_id, raster(2400, 800))

    second = await upload(client, staff_headers, kp_setup.event_id, raster(1200, 600))

    assert second.status_code == 200
    first_keys = {source["url"] for source in first.json()["sources"]}
    second_keys = {source["url"] for source in second.json()["sources"]}
    assert first_keys.isdisjoint(second_keys)
    assert len(s3_client.objects) == 2
    stored = await client.get(banner_url(kp_setup.event_id), headers=staff_headers)
    assert stored.json() == second.json()


async def test_reset_restores_the_default_and_removes_the_files(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
):
    await upload(client, staff_headers, kp_setup.event_id, raster(2400, 800))

    response = await client.delete(banner_url(kp_setup.event_id), headers=staff_headers)
    repeated = await client.delete(banner_url(kp_setup.event_id), headers=staff_headers)

    assert response.status_code == 200
    assert repeated.status_code == 200
    stored = await client.get(banner_url(kp_setup.event_id), headers=staff_headers)
    assert stored.json() is None
    assert s3_client.objects == {}


async def test_a_cloned_event_keeps_the_banner_of_its_source(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
):
    uploaded = await upload(client, staff_headers, kp_setup.event_id, raster(2400, 800))
    clone = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/clone",
        json=kp_payload("Cloned KP"),
        headers=staff_headers,
    )
    clone_id = clone.json()["id"]

    await client.delete(banner_url(kp_setup.event_id), headers=staff_headers)

    cloned = await client.get(banner_url(clone_id), headers=staff_headers)
    assert cloned.json() == uploaded.json()
    assert len(s3_client.objects) == len(BANNER_WIDTHS)


async def test_the_latest_event_carries_its_banner(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
):
    before = await client.get("/api/kp/latest", headers=company_headers)
    uploaded = await upload(client, staff_headers, kp_setup.event_id, raster(2400, 800))

    after = await client.get("/api/kp/latest", headers=company_headers)

    assert before.json()["banner"] is None
    assert after.json()["id"] == kp_setup.event_id
    assert after.json()["banner"] == uploaded.json()


async def test_a_company_cannot_change_the_banner(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    s3_client: FakeS3Client,
):
    response = await upload(
        client, company_headers, kp_setup.event_id, raster(1600, 500)
    )

    assert response.status_code == 403
    assert s3_client.objects == {}
