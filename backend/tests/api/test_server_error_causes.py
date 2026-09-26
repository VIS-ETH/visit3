import logging
import re
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock
from uuid import UUID

import grpc
import httpx
import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    StorageDeleteFailed,
    StorageDownloadFailed,
    StorageUploadFailed,
)
from app.core.service_account import OAuthTokenError
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.user_repository import UserRepository
from app.services.storage_service import StorageService
from tests.api.conftest import KpSetup
from tests.booklet_pdfs import make_pdf

REGISTER_PAYLOAD = {
    "email": "newcomer@example.com",
    "password": "a-long-enough-password",
    "first_name": "Ada",
    "last_name": "Lovelace",
}
INVITED_EMAIL = "invitee@example.com"
REQUIREMENT_DESCRIPTION = "Describe the booth layout in a few sentences."


class MailRpcError(grpc.RpcError):
    pass


def mail_text(message: object) -> str:
    return str(message)


def sent_links(mail_stub: AsyncMock, marker: str) -> list[str]:
    pattern = re.compile(re.escape(marker) + r"([^\s)\\\\\"']+)")
    return [
        match
        for call in mail_stub.SendMail.await_args_list
        for match in pattern.findall(mail_text(call.args[0]))
    ]


@pytest.mark.parametrize("failure", [MailRpcError(), OAuthTokenError("token")])
async def test_registration_reports_an_unavailable_mail_service(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    mail_stub: AsyncMock,
    failure: Exception,
):
    mail_stub.SendMail.side_effect = failure

    failed = await client.post(
        "/api/auth/register", json=REGISTER_PAYLOAD, headers=csrf_headers
    )
    mail_stub.SendMail.side_effect = None
    retried = await client.post(
        "/api/auth/register", json=REGISTER_PAYLOAD, headers=csrf_headers
    )

    assert failed.status_code == 503
    assert failed.json()["code"] == "error.mail_unavailable"
    assert retried.status_code == 200


async def test_password_reset_reports_an_unavailable_mail_service(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.side_effect = MailRpcError()

    response = await client.post(
        "/api/auth/reset-password",
        json={"email": company_user.email},
        headers=csrf_headers,
    )

    assert response.status_code == 503
    assert response.json()["code"] == "error.mail_unavailable"


async def test_a_failed_invite_mail_can_be_sent_again(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.side_effect = MailRpcError()
    failed = await client.post(
        "/api/company/invite", json={"email": INVITED_EMAIL}, headers=company_headers
    )
    mail_stub.SendMail.side_effect = None
    retried = await client.post(
        "/api/company/invite", json={"email": INVITED_EMAIL}, headers=company_headers
    )

    assert failed.status_code == 503
    assert failed.json()["code"] == "error.mail_unavailable"
    assert retried.status_code == 200


async def test_email_confirmation_survives_a_failed_staff_notification(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
):
    await client.post("/api/auth/register", json=REGISTER_PAYLOAD, headers=csrf_headers)
    token = sent_links(mail_stub, "/confirm-email/")[-1]
    mail_stub.SendMail.side_effect = MailRpcError()

    response = await client.post(
        f"/api/user/confirm-email/{token}", headers=csrf_headers
    )

    assert response.status_code == 200
    user = await UserRepository(db_session).get_by_email(REGISTER_PAYLOAD["email"])
    assert user is not None
    await db_session.refresh(user)
    assert user.email_confirmed is True


async def test_a_parallel_registration_with_the_same_email_is_refused(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    await client.post("/api/auth/register", json=REGISTER_PAYLOAD, headers=csrf_headers)

    async def nobody(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(UserRepository, "get_by_email", nobody)
    response = await client.post(
        "/api/auth/register", json=REGISTER_PAYLOAD, headers=csrf_headers
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.email_used"


async def test_setting_up_a_company_with_a_taken_name_is_refused(
    client: AsyncClient,
    db_session: AsyncSession,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    await CompanyRepository(db_session).create_company("Gamma AG")
    founder = await create_user(email="founder@example.com", password=None)

    async def no_company(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(CompanyRepository, "get_by_name", no_company)
    response = await client.post(
        "/api/company/setup",
        json={"name": "Gamma AG"},
        headers={**await auth_headers(founder), **csrf_headers},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.company_name_taken"


async def test_a_parallel_requirement_answer_is_saved_once(
    client: AsyncClient,
    kp_setup: KpSetup,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    monkeypatch: pytest.MonkeyPatch,
):
    await complete_company_profile(company_headers)
    service = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={
            "name": "Booth text",
            "price": 0,
            "requirements": [
                {
                    "type": "text",
                    "name": "Layout",
                    "description": REQUIREMENT_DESCRIPTION,
                }
            ],
        },
        headers=staff_headers,
    )
    booking = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={
            "booth_zone_id": kp_setup.booth_zone_id,
            "services": [{"service_id": service.json()["id"], "quantity": 1}],
            "confirm_profile": True,
        },
        headers=company_headers,
    )
    url = (
        f"/api/kp/booking-services/{booking.json()['services'][0]['id']}"
        f"/requirements/{service.json()['requirements'][0]['id']}/text"
    )
    await client.put(url, json={"text_value": "First tab"}, headers=company_headers)

    async def not_found_yet(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(KpRepository, "get_requirement_file", not_found_yet)
    response = await client.put(
        url, json={"text_value": "Second tab"}, headers=company_headers
    )
    monkeypatch.undo()
    stored = await client.get(url, headers=company_headers)

    assert response.status_code == 200
    assert stored.json()["text_value"] == "Second tab"


async def test_confirming_twice_keeps_the_booking_confirmed(
    client: AsyncClient,
    kp_setup: KpSetup,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
):
    booking_id = (await register_booking(company_headers, kp_setup)).json()["id"]

    first = await client.post(
        f"/api/kp/bookings/{booking_id}/accept", headers=staff_headers
    )
    second = await client.post(
        f"/api/kp/bookings/{booking_id}/accept", headers=staff_headers
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "CONFIRMED"
    assert second.json()["confirmed_at"] == first.json()["confirmed_at"]


async def test_accepting_an_invite_twice_keeps_the_membership(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    from datetime import datetime, timedelta, timezone

    assert company_user.company_id is not None
    await CompanyRepository(db_session).create_invite(
        "double-token",
        company_user.company_id,
        INVITED_EMAIL,
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    invitee = await create_user(email=INVITED_EMAIL, password=None)
    headers = {**await auth_headers(invitee), **csrf_headers}

    first = await client.post(
        "/api/company/invite/double-token/accept", headers=headers
    )
    second = await client.post(
        "/api/company/invite/double-token/accept", headers=headers
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert UUID(second.json()["company_id"]) == company_user.company_id


async def test_an_unreachable_identity_provider_redirects_to_the_login(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def unreachable(*_args: object, **_kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("identity provider down")

    monkeypatch.setattr(httpx.AsyncClient, "post", unreachable)
    client.cookies.set("oauth_state", "matching-state")

    response = await client.get(
        "/api/auth/callback?code=auth-code&state=matching-state"
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"{get_settings().VISIT_FRONTEND_SERVER_URL}/login?error=server.error"
    )


async def test_an_unexpected_error_carries_a_request_id(
    client: AsyncClient,
    storage_service: StorageService,
    company_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
):
    storage_service.upload_bytes.side_effect = RuntimeError("boom")

    with caplog.at_level(logging.ERROR):
        response = await client.post(
            "/api/company/me/profile/logo",
            files={"file": ("logo.png", b"\x89PNG\r\n\x1a\n" + b"0" * 16, "image/png")},
            headers=company_headers,
        )

    request_id = response.headers["x-request-id"]
    assert response.status_code == 500
    assert response.json()["requestId"] == request_id
    assert any(request_id in record.getMessage() for record in caplog.records)


async def test_every_response_carries_a_request_id(client: AsyncClient):
    response = await client.get("/health")

    assert response.headers["x-request-id"]


def booklet_background_url(event_id: str) -> str:
    return f"/api/kp/events/{event_id}/booklet/background"


async def upload_booklet_background(
    client: AsyncClient, headers: dict[str, str], event_id: str, content: bytes
) -> Response:
    return await client.put(
        booklet_background_url(event_id),
        files={"file": ("booklet.pdf", content, "application/pdf")},
        headers=headers,
    )


async def test_a_replaced_booklet_background_survives_a_failed_cleanup(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
):
    await upload_booklet_background(
        client, staff_headers, kp_setup.event_id, make_pdf()
    )
    storage_service.delete_object.side_effect = StorageDeleteFailed("cleanup")

    response = await upload_booklet_background(
        client, staff_headers, kp_setup.event_id, make_pdf(fill="#eeeeee")
    )
    stored = await client.get(
        booklet_background_url(kp_setup.event_id), headers=staff_headers
    )

    assert response.status_code == 200
    assert stored.json() == response.json()


async def test_a_booklet_background_reset_survives_a_failed_cleanup(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
):
    await upload_booklet_background(
        client, staff_headers, kp_setup.event_id, make_pdf()
    )
    storage_service.delete_object.side_effect = StorageDeleteFailed("cleanup")

    response = await client.delete(
        booklet_background_url(kp_setup.event_id), headers=staff_headers
    )
    stored = await client.get(
        booklet_background_url(kp_setup.event_id), headers=staff_headers
    )

    assert response.status_code == 200
    assert stored.json() is None


async def test_a_storage_outage_on_booklet_upload_carries_a_request_id(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
    caplog: pytest.LogCaptureFixture,
):
    storage_service.upload_bytes.side_effect = StorageUploadFailed("outage")

    with caplog.at_level(logging.ERROR):
        response = await upload_booklet_background(
            client, staff_headers, kp_setup.event_id, make_pdf()
        )
    stored = await client.get(
        booklet_background_url(kp_setup.event_id), headers=staff_headers
    )

    request_id = response.headers["x-request-id"]
    assert response.status_code == 503
    assert response.json()["code"] == "error.storage_upload_failed"
    assert response.json()["requestId"] == request_id
    assert any(request_id in record.getMessage() for record in caplog.records)
    assert stored.json() is None


async def test_a_storage_outage_on_booklet_preview_carries_a_request_id(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    storage_service: AsyncMock,
):
    await upload_booklet_background(
        client, staff_headers, kp_setup.event_id, make_pdf()
    )
    storage_service.download_bytes.side_effect = StorageDownloadFailed("outage")

    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booklet/preview", headers=staff_headers
    )

    assert response.status_code == 500
    assert response.json()["code"] == "error.storage_download_failed"
    assert response.json()["requestId"] == response.headers["x-request-id"]


async def test_a_client_error_carries_no_request_id_in_the_body(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await upload_booklet_background(
        client, staff_headers, kp_setup.event_id, b"not a pdf"
    )

    assert response.status_code == 400
    assert "requestId" not in response.json()
    assert response.headers["x-request-id"]
