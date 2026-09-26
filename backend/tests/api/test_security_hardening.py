from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.types import Message

from app.core.config import Settings, get_settings
from app.models.user import User
from tests.api.conftest import DEFAULT_PASSWORD

MEGABYTE = 1024 * 1024
OVERSIZED_BODY_BYTES = 40 * MEGABYTE
CHUNK_BYTES = MEGABYTE
BOUNDARY = "sec-boundary"


def _settings(**overrides: Any) -> Settings:
    return Settings.model_validate({**get_settings().model_dump(), **overrides})


async def _bytes_read_by_app(
    app: FastAPI, path: str, content_type: str, body_prefix: bytes, total: int
) -> tuple[int, int]:
    consumed = 0
    sent = 0
    status: list[int] = []
    payload_bytes = total - len(body_prefix)
    headers = [
        (b"content-type", content_type.encode()),
        (b"content-length", str(total).encode()),
    ]
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("203.0.113.9", 50000),
        "server": ("test", 443),
    }

    async def receive() -> Message:
        nonlocal consumed, sent
        if sent == 0:
            sent = 1
            consumed += len(body_prefix)
            return {"type": "http.request", "body": body_prefix, "more_body": True}
        remaining = payload_bytes - (sent - 1) * CHUNK_BYTES
        if remaining <= 0:
            return {"type": "http.disconnect"}
        chunk = b"a" * min(CHUNK_BYTES, remaining)
        sent += 1
        consumed += len(chunk)
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": remaining > CHUNK_BYTES,
        }

    async def send(message: Message) -> None:
        if message["type"] == "http.response.start":
            status.append(message["status"])

    await app(scope, receive, send)
    return consumed, status[0]


def test_production_refuses_the_keycloak_admin_debug_switch():
    with pytest.raises(ValueError):
        _settings(DEBUG=False, DEBUG_KEYCLOAK_ADMIN=True)


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
async def test_api_documentation_is_hidden_in_production(
    client: AsyncClient, path: str
):
    assert get_settings().DEBUG is False

    response = await client.get(path)

    assert response.status_code == 404


async def test_api_responses_forbid_content_sniffing(client: AsyncClient):
    response = await client.get("/api/csrftoken")

    assert response.headers.get("x-content-type-options") == "nosniff"


async def test_token_responses_are_not_cached(
    client: AsyncClient, csrf_headers: dict[str, str], company_user: User
):
    response = await client.post(
        "/api/auth/login",
        data={"username": company_user.email, "password": DEFAULT_PASSWORD},
        headers=csrf_headers,
    )

    assert response.status_code == 200
    assert "no-store" in response.headers.get("cache-control", "")


async def test_an_anonymous_upload_is_refused_before_it_is_read(api_app: FastAPI):
    prefix = (
        f"--{BOUNDARY}\r\n"
        'Content-Disposition: form-data; name="file"; filename="logo.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode()

    consumed, status = await _bytes_read_by_app(
        api_app,
        "/api/company/me/profile/logo",
        f"multipart/form-data; boundary={BOUNDARY}",
        prefix,
        OVERSIZED_BODY_BYTES,
    )

    assert status in {401, 403, 413}
    assert consumed < 2 * MEGABYTE


async def test_an_anonymous_json_body_is_bounded(api_app: FastAPI):
    consumed, status = await _bytes_read_by_app(
        api_app,
        "/api/auth/register",
        "application/json",
        b'{"email": "a@example.com", "first_name": "',
        OVERSIZED_BODY_BYTES,
    )

    assert status == 413
    assert consumed < 2 * MEGABYTE


async def test_repeated_failed_logins_are_throttled(
    client: AsyncClient, csrf_headers: dict[str, str], company_user: User
):
    statuses = [
        (
            await client.post(
                "/api/auth/login",
                data={"username": company_user.email, "password": f"guess-{attempt}"},
                headers=csrf_headers,
            )
        ).status_code
        for attempt in range(30)
    ]

    assert 429 in statuses
