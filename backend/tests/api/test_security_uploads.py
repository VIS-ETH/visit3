import struct
import zlib
from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from httpx import AsyncClient, Response

from app.core.config import get_settings
from app.services.storage_service import StorageService
from tests.api.conftest import PNG_BYTES, KpSetup
from tests.api.test_upload_routes import FakeS3Client, ImageRequirement

HTML_BYTES = b"<!DOCTYPE html><html><body><script>alert(document.domain)</script>"
SVG_BYTES = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'
STREAM_LIMIT_BYTES = 64 * 1024
STREAMED_BYTES = 8 * 1024 * 1024
STREAM_CHUNK_BYTES = 64 * 1024
BOUNDARY = "sec-boundary"
BOMB_SIDE = 30_000
MAX_LOGO_PIXELS = 40_000_000


def png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def decompression_bomb(side: int) -> bytes:
    header = struct.pack(">IIBBBBB", side, side, 8, 0, 0, 0, 0)
    compressor = zlib.compressobj(9)
    row = b"\x00" * (side + 1)
    pixels = b"".join(compressor.compress(row) for _ in range(side))
    pixels += compressor.flush()
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", pixels)
        + png_chunk(b"IEND", b"")
    )


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


@pytest.fixture
async def file_requirement(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> ImageRequirement:
    service = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={
            "name": "Print data",
            "price": 0,
            "requirements": [
                {
                    "type": "file",
                    "name": "Artwork",
                    "description": "Upload the artwork for the booth banner.",
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


@pytest.mark.parametrize(
    ("filename", "content", "declared_type"),
    [
        ("artwork.html", HTML_BYTES, "text/html"),
        ("artwork.svg", SVG_BYTES, "image/svg+xml"),
    ],
)
async def test_generic_requirement_upload_does_not_store_the_declared_active_type(
    client: AsyncClient,
    s3_client: FakeS3Client,
    company_headers: dict[str, str],
    file_requirement: ImageRequirement,
    filename: str,
    content: bytes,
    declared_type: str,
):
    response = await client.post(
        f"/api/kp/booking-services/{file_requirement.booking_service_id}"
        f"/requirements/{file_requirement.requirement_id}/file",
        files={"file": (filename, content, declared_type)},
        headers=company_headers,
    )

    assert response.status_code == 200
    [(_, stored_type)] = s3_client.objects.values()
    assert stored_type == "application/octet-stream"


async def test_logo_upload_rejects_a_decompression_bomb(
    client: AsyncClient,
    s3_client: FakeS3Client,
    company_headers: dict[str, str],
):
    bomb = decompression_bomb(BOMB_SIDE)
    assert len(bomb) < get_settings().STORAGE_IMAGE_MAX_SIZE_BYTES
    assert BOMB_SIDE * BOMB_SIDE > MAX_LOGO_PIXELS

    response = await client.post(
        "/api/company/me/profile/logo",
        files={"file": ("logo.png", bomb, "image/png")},
        headers=company_headers,
    )

    assert response.status_code == 400
    assert s3_client.objects == {}


async def test_upload_size_limit_stops_reading_an_oversized_body(
    client: AsyncClient,
    storage_service: StorageService,
    company_headers: dict[str, str],
):
    storage_service.settings = storage_service.settings.model_copy(
        update={"STORAGE_IMAGE_MAX_SIZE_BYTES": STREAM_LIMIT_BYTES}
    )
    prefix = (
        f"--{BOUNDARY}\r\n"
        'Content-Disposition: form-data; name="file"; filename="logo.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + PNG_BYTES
    suffix = f"\r\n--{BOUNDARY}--\r\n".encode()
    consumed = 0

    async def body() -> AsyncIterator[bytes]:
        nonlocal consumed
        for part in (
            prefix,
            *[b"\x00" * STREAM_CHUNK_BYTES] * (STREAMED_BYTES // STREAM_CHUNK_BYTES),
            suffix,
        ):
            consumed += len(part)
            yield part

    total = len(prefix) + STREAMED_BYTES + len(suffix)
    response = await client.post(
        "/api/company/me/profile/logo",
        content=body(),
        headers={
            **company_headers,
            "Content-Type": f"multipart/form-data; boundary={BOUNDARY}",
            "Content-Length": str(total),
        },
    )

    assert response.status_code in (400, 413)
    assert consumed < STREAMED_BYTES // 4
