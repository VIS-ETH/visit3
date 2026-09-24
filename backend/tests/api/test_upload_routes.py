import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest
from httpx import AsyncClient, Response

from app.core.config import get_settings
from app.services.storage_service import StorageService
from tests.api.conftest import PNG_BYTES, KpSetup

HTML_BYTES = b"<!DOCTYPE html><html><body>not a png</body></html>"
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n" + b"\x00" * 32
SVG_BYTES = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 16
IMAGE_LIMIT_BYTES = 128
NAMETAG_BACKGROUND = "exports/nametags/background"


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(
        self, *, Bucket: str, Key: str, Body: bytes, ContentType: str
    ) -> dict[str, Any]:
        self.objects[Key] = (Body, ContentType)
        return {"ETag": f'"{hashlib.sha256(Body).hexdigest()}"'}

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.objects.pop(Key, None)

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        content, _ = self.objects[Key]
        return {"Body": FakeBody(content)}

    def generate_presigned_url(
        self, operation: str, *, Params: dict[str, str], ExpiresIn: int
    ) -> str:
        return f"https://storage.test/{Params['Key']}"


class FakeBody:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def read(self) -> bytes:
        return self.content


@dataclass(frozen=True)
class ImageRequirement:
    booking_service_id: str
    requirement_id: str


@pytest.fixture
def s3_client() -> FakeS3Client:
    return FakeS3Client()


@pytest.fixture
def storage_service(s3_client: FakeS3Client) -> StorageService:
    service = StorageService.__new__(StorageService)
    service.settings = get_settings().model_copy(
        update={
            "STORAGE_IMAGE_MAX_SIZE_BYTES": IMAGE_LIMIT_BYTES,
            "S3_PUBLIC_ENDPOINT_URL": None,
        }
    )
    service.client = s3_client
    return service


@pytest.fixture
async def image_requirement(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> ImageRequirement:
    service = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={
            "name": "Company logo",
            "price": 0,
            "requirements": [
                {
                    "type": "image",
                    "name": "Logo",
                    "description": "Upload your company logo as a png image.",
                }
            ],
        },
        headers=staff_headers,
    )
    await complete_company_profile(company_headers)
    booking = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={
            "booth_zone_id": kp_setup.booth_zone_id,
            "services": [{"service_id": service.json()["id"], "quantity": 1}],
            "confirm_profile": True,
        },
        headers=company_headers,
    )
    return ImageRequirement(
        booking_service_id=booking.json()["services"][0]["id"],
        requirement_id=service.json()["requirements"][0]["id"],
    )


def requirement_file_url(requirement: ImageRequirement) -> str:
    return (
        f"/api/kp/booking-services/{requirement.booking_service_id}"
        f"/requirements/{requirement.requirement_id}/file"
    )


async def test_requirement_upload_stores_the_sniffed_image_type(
    client: AsyncClient,
    s3_client: FakeS3Client,
    company_headers: dict[str, str],
    image_requirement: ImageRequirement,
):
    response = await client.post(
        requirement_file_url(image_requirement),
        files={"file": ("logo.png", PNG_BYTES, "image/png")},
        headers=company_headers,
    )

    assert response.status_code == 200
    stored_file = response.json()["stored_file"]
    assert stored_file["mime_type"] == "image/png"
    assert stored_file["size_bytes"] == len(PNG_BYTES)
    assert stored_file["sha256"] == hashlib.sha256(PNG_BYTES).hexdigest()
    assert list(s3_client.objects.values()) == [(PNG_BYTES, "image/png")]


async def test_requirement_upload_rejects_html_declared_as_png(
    client: AsyncClient,
    s3_client: FakeS3Client,
    company_headers: dict[str, str],
    image_requirement: ImageRequirement,
):
    response = await client.post(
        requirement_file_url(image_requirement),
        files={"file": ("logo.png", HTML_BYTES, "image/png")},
        headers=company_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.storage_file_invalid_mime_type"
    assert s3_client.objects == {}


async def test_requirement_upload_rejects_a_file_over_the_image_limit(
    client: AsyncClient,
    s3_client: FakeS3Client,
    company_headers: dict[str, str],
    image_requirement: ImageRequirement,
):
    oversize = PNG_BYTES + b"\x00" * IMAGE_LIMIT_BYTES

    response = await client.post(
        requirement_file_url(image_requirement),
        files={"file": ("logo.png", oversize, "image/png")},
        headers=company_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.storage_file_too_large"
    assert s3_client.objects == {}


async def test_nametag_background_accepts_a_real_png(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
):
    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/{NAMETAG_BACKGROUND}",
        files={"file": ("background.png", PNG_BYTES, "image/png")},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["stored_file"]["mime_type"] == "image/png"
    assert list(s3_client.objects.values()) == [(PNG_BYTES, "image/png")]


async def test_nametag_background_rejects_a_pdf(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
):
    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/{NAMETAG_BACKGROUND}",
        files={"file": ("background.pdf", PDF_BYTES, "application/pdf")},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.storage_file_invalid_mime_type"
    assert s3_client.objects == {}


@pytest.fixture
async def venue_layout_id(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
) -> str:
    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/venue-layouts",
        json={"name": "Einstein"},
        headers=staff_headers,
    )
    return response.json()["id"]


def venue_background_url(layout_id: str) -> str:
    return f"/api/kp/venue-layouts/{layout_id}/background"


@pytest.mark.parametrize(
    ("upload", "mime_type"),
    [
        (("plan.png", PNG_BYTES, "image/png"), "image/png"),
        (("plan.webp", WEBP_BYTES, "image/webp"), "image/webp"),
    ],
)
async def test_venue_background_stores_the_sniffed_image_type(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    venue_layout_id: str,
    upload: tuple[str, bytes, str],
    mime_type: str,
):
    response = await client.put(
        venue_background_url(venue_layout_id),
        files={"file": upload},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["background_file"]["mime_type"] == mime_type
    assert response.json()["background_url"].startswith("https://storage.test/")
    assert list(s3_client.objects.values()) == [(upload[1], mime_type)]


@pytest.mark.parametrize(
    "upload",
    [
        ("plan.svg", SVG_BYTES, "image/svg+xml"),
        ("plan.png", HTML_BYTES, "image/png"),
        ("plan.pdf", PDF_BYTES, "application/pdf"),
    ],
)
async def test_venue_background_rejects_a_file_that_is_not_a_raster_image(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    venue_layout_id: str,
    upload: tuple[str, bytes, str],
):
    response = await client.put(
        venue_background_url(venue_layout_id),
        files={"file": upload},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.storage_file_invalid_mime_type"
    assert s3_client.objects == {}


async def test_venue_background_replaces_the_previous_object(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    venue_layout_id: str,
):
    first = await client.put(
        venue_background_url(venue_layout_id),
        files={"file": ("plan.png", PNG_BYTES, "image/png")},
        headers=staff_headers,
    )

    response = await client.put(
        venue_background_url(venue_layout_id),
        files={"file": ("plan.webp", WEBP_BYTES, "image/webp")},
        headers=staff_headers,
    )

    assert first.status_code == 200
    assert response.status_code == 200
    assert list(s3_client.objects.values()) == [(WEBP_BYTES, "image/webp")]
    assert (
        response.json()["background_file"]["id"]
        != first.json()["background_file"]["id"]
    )


async def test_venue_background_is_deleted_with_its_object(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    venue_layout_id: str,
):
    await client.put(
        venue_background_url(venue_layout_id),
        files={"file": ("plan.png", PNG_BYTES, "image/png")},
        headers=staff_headers,
    )

    response = await client.delete(
        venue_background_url(venue_layout_id), headers=staff_headers
    )

    assert response.status_code == 200
    assert response.json()["background_file"] is None
    assert response.json()["background_url"] is None
    assert s3_client.objects == {}


async def test_deleting_a_layout_removes_its_background_object(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    venue_layout_id: str,
):
    await client.put(
        venue_background_url(venue_layout_id),
        files={"file": ("plan.png", PNG_BYTES, "image/png")},
        headers=staff_headers,
    )

    response = await client.delete(
        f"/api/kp/venue-layouts/{venue_layout_id}", headers=staff_headers
    )
    layouts = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue-layouts", headers=staff_headers
    )

    assert response.status_code == 200
    assert layouts.json() == []
    assert s3_client.objects == {}


def zone_layout_url(booth_zone_id: str) -> str:
    return f"/api/kp/booth-zones/{booth_zone_id}/layout-file"


@pytest.mark.parametrize(
    ("upload", "mime_type"),
    [
        (("layout.png", PNG_BYTES, "image/png"), "image/png"),
        (("layout.pdf", PDF_BYTES, "application/pdf"), "application/pdf"),
    ],
)
async def test_zone_layout_accepts_an_image_and_a_pdf(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    upload: tuple[str, bytes, str],
    mime_type: str,
):
    response = await client.put(
        zone_layout_url(kp_setup.booth_zone_id),
        files={"file": upload},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["layout_url"].startswith("https://storage.test/")
    assert list(s3_client.objects.values()) == [(upload[1], mime_type)]


@pytest.mark.parametrize(
    "upload",
    [
        ("layout.svg", SVG_BYTES, "image/svg+xml"),
        ("layout.png", HTML_BYTES, "image/png"),
    ],
)
async def test_zone_layout_rejects_a_file_that_is_neither_image_nor_pdf(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    upload: tuple[str, bytes, str],
):
    response = await client.put(
        zone_layout_url(kp_setup.booth_zone_id),
        files={"file": upload},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.storage_file_invalid_mime_type"
    assert s3_client.objects == {}


async def test_zone_layout_replaces_the_previous_object(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
):
    first = await client.put(
        zone_layout_url(kp_setup.booth_zone_id),
        files={"file": ("layout.png", PNG_BYTES, "image/png")},
        headers=staff_headers,
    )

    response = await client.put(
        zone_layout_url(kp_setup.booth_zone_id),
        files={"file": ("layout.pdf", PDF_BYTES, "application/pdf")},
        headers=staff_headers,
    )

    assert first.status_code == 200
    assert response.status_code == 200
    assert list(s3_client.objects.values()) == [(PDF_BYTES, "application/pdf")]


async def test_zone_layout_is_deleted_with_its_object(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
):
    await client.put(
        zone_layout_url(kp_setup.booth_zone_id),
        files={"file": ("layout.png", PNG_BYTES, "image/png")},
        headers=staff_headers,
    )

    response = await client.delete(
        zone_layout_url(kp_setup.booth_zone_id), headers=staff_headers
    )

    assert response.status_code == 200
    assert response.json()["layout_url"] is None
    assert s3_client.objects == {}


async def test_deleting_a_zone_removes_its_layout_object(
    client: AsyncClient,
    s3_client: FakeS3Client,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
):
    await client.put(
        zone_layout_url(kp_setup.booth_zone_id),
        files={"file": ("layout.png", PNG_BYTES, "image/png")},
        headers=staff_headers,
    )

    response = await client.delete(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}", headers=staff_headers
    )
    zones = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones", headers=staff_headers
    )

    assert response.status_code == 200
    assert zones.json() == []
    assert s3_client.objects == {}
