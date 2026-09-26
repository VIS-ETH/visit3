import logging
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient, Response
from starlette.types import Message, Receive, Scope, Send

from app.core.exception_handlers import UnexpectedErrorMiddleware
from tests.api.conftest import KpSetup

INJECTED_HEADER = "Acme\r\nBcc: victim@example.com"
FORGED_LOG_LINE = (
    "nobody@example.com\nINFO:app.services.auth_service:"
    "User login successful: admin@vis.ethz.ch"
)
MEGABYTE_TEXT = "A" * (1024 * 1024)
OVERFLOWING_PAGE = 10**18


async def test_company_name_cannot_inject_mail_headers(
    client: AsyncClient,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    await client.patch(
        "/api/company/me", json={"name": INJECTED_HEADER}, headers=company_headers
    )

    await client.post(
        "/api/company/invite",
        json={"email": "invitee@example.com"},
        headers=company_headers,
    )

    [call] = mail_stub.SendMail.await_args_list
    subject = call.args[0].subject
    assert "\r" not in subject
    assert "\n" not in subject


async def test_failed_login_cannot_forge_log_lines(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
):
    with caplog.at_level(logging.INFO):
        response = await client.post(
            "/api/auth/login",
            data={"username": FORGED_LOG_LINE, "password": "wrong-password"},
            headers=csrf_headers,
        )

    assert response.status_code == 400
    assert all("\n" not in record.getMessage() for record in caplog.records)


@pytest.fixture
async def text_requirement_url(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> str:
    service = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={
            "name": "Booth sign",
            "price": 0,
            "requirements": [
                {
                    "type": "text",
                    "name": "Sign text",
                    "description": "The text printed on the booth sign.",
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
    return (
        f"/api/kp/booking-services/{booking.json()['services'][0]['id']}"
        f"/requirements/{service.json()['requirements'][0]['id']}/text"
    )


async def test_requirement_text_is_capped(
    client: AsyncClient,
    company_headers: dict[str, str],
    text_requirement_url: str,
):
    response = await client.put(
        text_requirement_url,
        json={"text_value": MEGABYTE_TEXT},
        headers=company_headers,
    )

    assert response.status_code == 422


async def test_company_name_is_capped(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.patch(
        "/api/company/me", json={"name": MEGABYTE_TEXT}, headers=company_headers
    )

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["brand_name", "places_of_work", "billing_city"])
async def test_company_profile_text_fields_are_capped(
    client: AsyncClient,
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    field: str,
):
    response = await complete_company_profile(company_headers, **{field: MEGABYTE_TEXT})

    assert response.status_code == 422


async def test_user_list_rejects_a_page_beyond_the_offset_range(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.get(
        "/api/users", params={"page": OVERFLOWING_PAGE}, headers=staff_headers
    )

    assert response.status_code == 422


async def test_an_unexpected_error_on_a_crafted_path_logs_one_line(
    caplog: pytest.LogCaptureFixture,
):
    async def failing_app(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("boom")

    async def receive() -> Message:
        return {"type": "http.request", "body": b""}

    async def send(message: Message) -> None:
        return None

    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/x\nINFO:app:forged",
        "headers": [],
    }
    with caplog.at_level(logging.INFO):
        await UnexpectedErrorMiddleware(failing_app)(scope, receive, send)

    assert caplog.records
    assert all("\n" not in record.getMessage() for record in caplog.records)


async def test_company_search_rejects_a_page_beyond_the_offset_range(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.get(
        "/api/companies", params={"page": OVERFLOWING_PAGE}, headers=staff_headers
    )

    assert response.status_code == 422
