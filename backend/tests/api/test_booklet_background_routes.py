from base64 import b64decode
from collections.abc import Awaitable, Callable, Iterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response

from app.core import deps
from app.models.user import User
from app.services.booklet_service import BOOKLET_BACKGROUND_MAX_BYTES
from app.services.pdf_service import PdfService, RenderedImage
from app.services.typst_runner import TypstRenderAborted
from tests.api.conftest import PNG_BYTES, KpSetup, company_profile_payload, kp_payload
from tests.booklet_pdfs import make_pdf

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def background_url(event_id: str) -> str:
    return f"/api/kp/events/{event_id}/booklet/background"


def preview_url(event_id: str) -> str:
    return f"/api/kp/events/{event_id}/booklet/preview"


async def upload(
    client: AsyncClient,
    headers: dict[str, str],
    event_id: str,
    content: bytes,
    filename: str = "booklet.pdf",
) -> Response:
    return await client.put(
        background_url(event_id),
        files={"file": (filename, content, "application/pdf")},
        headers=headers,
    )


class RecordingPdfService(PdfService):
    def __init__(self) -> None:
        self.renders: list[dict[str, Any]] = []

    async def render_png(self, **kwargs: Any) -> RenderedImage:
        self.renders.append(kwargs)
        return await super().render_png(**kwargs)


@pytest.fixture
def recording_pdf_service(api_app: FastAPI) -> Iterator[RecordingPdfService]:
    service = RecordingPdfService()
    api_app.dependency_overrides[deps.get_pdf_service] = lambda: service
    yield service
    api_app.dependency_overrides.pop(deps.get_pdf_service, None)


class OverloadedPdfService(PdfService):
    def __init__(self, abort_inspection: bool) -> None:
        self.abort_inspection = abort_inspection

    async def inspect_pdf(self, content: bytes, timeout: float | None = None) -> Any:
        if self.abort_inspection:
            raise TypstRenderAborted("timeout")
        return await super().inspect_pdf(content, timeout)

    async def render_png(self, **kwargs: Any) -> RenderedImage:
        raise TypstRenderAborted("timeout")


@pytest.fixture
def overloaded_pdf_service(api_app: FastAPI) -> Iterator[Callable[[bool], None]]:
    def _install(abort_inspection: bool) -> None:
        service = OverloadedPdfService(abort_inspection)
        api_app.dependency_overrides[deps.get_pdf_service] = lambda: service

    yield _install
    api_app.dependency_overrides.pop(deps.get_pdf_service, None)


@pytest.fixture
async def plain_staff_headers(
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(staff_user), **csrf_headers}


async def stored_background(
    client: AsyncClient, headers: dict[str, str], event_id: str
) -> Any:
    return (await client.get(background_url(event_id), headers=headers)).json()


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (PNG_BYTES, "error.booklet_background_not_pdf"),
        (make_pdf(pages=2), "error.booklet_background_page_count"),
        (make_pdf(210, 297), "error.booklet_background_page_size"),
        (b"%PDF-1.7\nnot really a pdf", "error.booklet_background_unreadable"),
    ],
)
async def test_an_unusable_background_is_rejected_and_never_stored(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
    content: bytes,
    code: str,
):
    response = await upload(client, staff_headers, kp_setup.event_id, content)

    assert response.status_code == 400
    assert response.json()["code"] == code
    storage_service.upload_bytes.assert_not_awaited()
    assert await stored_background(client, staff_headers, kp_setup.event_id) is None


@pytest.mark.parametrize("abort_inspection", [True, False])
async def test_a_background_too_complex_to_render_is_rejected_and_never_stored(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
    overloaded_pdf_service: Callable[[bool], None],
    abort_inspection: bool,
):
    overloaded_pdf_service(abort_inspection)

    response = await upload(client, staff_headers, kp_setup.event_id, make_pdf())

    assert response.status_code == 400
    assert response.json()["code"] == "error.booklet_background_too_complex"
    storage_service.upload_bytes.assert_not_awaited()
    assert await stored_background(client, staff_headers, kp_setup.event_id) is None


async def test_an_admin_preview_that_renders_too_long_is_reported(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    overloaded_pdf_service: Callable[[bool], None],
):
    overloaded_pdf_service(False)

    response = await client.post(preview_url(kp_setup.event_id), headers=staff_headers)

    assert response.status_code == 503
    assert response.json()["code"] == "error.booklet_page_render_timeout"


async def test_a_background_over_the_size_limit_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
):
    oversized = make_pdf() + b"\n%" + b"x" * BOOKLET_BACKGROUND_MAX_BYTES

    response = await upload(client, staff_headers, kp_setup.event_id, oversized)

    assert response.status_code == 400
    assert response.json()["code"] == "error.booklet_background_too_large"
    storage_service.upload_bytes.assert_not_awaited()


async def test_an_a5_background_is_stored_and_offered_for_download(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
):
    content = make_pdf()

    response = await upload(client, staff_headers, kp_setup.event_id, content)
    stored = await stored_background(client, staff_headers, kp_setup.event_id)

    assert response.status_code == 200
    assert stored["filename"] == "booklet.pdf"
    assert stored["size_bytes"] == len(content)
    assert stored["download_url"] == "https://storage.test/download"
    storage_service.upload_bytes.assert_awaited_once()
    assert storage_service.upload_bytes.await_args.kwargs["content_type"] == (
        "application/pdf"
    )


async def test_nothing_is_offered_for_download_without_a_background(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    assert await stored_background(client, staff_headers, kp_setup.event_id) is None


async def test_reset_returns_to_the_built_in_design(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
):
    await upload(client, staff_headers, kp_setup.event_id, make_pdf())
    storage_key = storage_service.upload_bytes.await_args.kwargs["key"]

    response = await client.delete(
        background_url(kp_setup.event_id), headers=staff_headers
    )

    assert response.status_code == 200
    assert await stored_background(client, staff_headers, kp_setup.event_id) is None
    storage_service.delete_object.assert_awaited_with(storage_key)


async def test_replacing_a_background_deletes_the_old_file(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
):
    await upload(client, staff_headers, kp_setup.event_id, make_pdf())
    first_key = storage_service.upload_bytes.await_args.kwargs["key"]

    await upload(client, staff_headers, kp_setup.event_id, make_pdf(fill="#eeeeee"))

    storage_service.delete_object.assert_awaited_with(first_key)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "background"),
        ("PUT", "background"),
        ("DELETE", "background"),
        ("POST", "preview"),
    ],
)
async def test_only_admins_manage_the_booklet_design(
    client: AsyncClient,
    plain_staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    method: str,
    path: str,
):
    url = f"/api/kp/events/{kp_setup.event_id}/booklet/{path}"
    files = {"file": ("booklet.pdf", make_pdf(), "application/pdf")}

    for headers in (plain_staff_headers, company_headers):
        response = await client.request(
            method, url, headers=headers, files=files if method == "PUT" else None
        )
        assert response.status_code == 403


async def test_the_admin_preview_renders_sample_data_without_a_background(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    recording_pdf_service: RecordingPdfService,
):
    response = await client.post(preview_url(kp_setup.event_id), headers=staff_headers)

    assert response.status_code == 200
    assert b64decode(response.json()["png_base64"]).startswith(PNG_SIGNATURE)
    render = recording_pdf_service.renders[-1]
    assert render["data"]["background_path"] is None
    assert render["data"]["brand_name"]


async def test_the_admin_preview_uses_the_uploaded_background(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
    recording_pdf_service: RecordingPdfService,
):
    content = make_pdf(fill="#123456")
    await upload(client, staff_headers, kp_setup.event_id, content)
    storage_service.download_bytes.return_value = content

    response = await client.post(preview_url(kp_setup.event_id), headers=staff_headers)

    assert response.status_code == 200
    render = recording_pdf_service.renders[-1]
    assert render["data"]["background_path"] == "background.pdf"
    assert render["files"]["background.pdf"] == content


async def test_the_company_preview_uses_the_background_of_its_event(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
    register_booking: Callable[..., Awaitable[Response]],
    recording_pdf_service: RecordingPdfService,
):
    await register_booking(company_headers, kp_setup)
    content = make_pdf(fill="#123456")
    await upload(client, staff_headers, kp_setup.event_id, content)
    storage_service.download_bytes.return_value = content

    response = await client.post(
        "/api/company/me/profile/booklet-page",
        json=company_profile_payload(),
        headers=company_headers,
    )

    assert response.status_code == 200
    render = recording_pdf_service.renders[-1]
    assert render["data"]["background_path"] == "background.pdf"
    assert render["files"]["background.pdf"] == content


async def test_a_cloned_event_keeps_the_background_of_its_source(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
):
    await upload(client, staff_headers, kp_setup.event_id, make_pdf())
    clone = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/clone",
        json=kp_payload("Cloned KP"),
        headers=staff_headers,
    )
    clone_id = clone.json()["id"]

    await client.delete(background_url(kp_setup.event_id), headers=staff_headers)

    assert (await stored_background(client, staff_headers, clone_id))[
        "filename"
    ] == "booklet.pdf"
    storage_service.delete_object.assert_not_awaited()
