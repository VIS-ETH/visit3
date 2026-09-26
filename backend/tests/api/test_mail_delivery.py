from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.services.auth_service import AuthService
from tests.api.conftest import decoded_subject


def sent_message(mail_stub: AsyncMock) -> object:
    mail_stub.SendMail.assert_awaited_once()
    return mail_stub.SendMail.await_args.args[0]


def recipients(message: object) -> list[str]:
    return [address.mail_address.address for address in getattr(message, "to")]


@pytest.fixture
async def unconfirmed_company_user(
    create_user: Callable[..., Awaitable[User]],
) -> User:
    return await create_user(
        email="pending@example.com",
        company_name="Pending AG",
        user_confirmed=False,
        email_confirmed=False,
    )


async def test_registration_sends_the_confirm_email_mail(
    client: AsyncClient, csrf_headers: dict[str, str], mail_stub: AsyncMock
):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newcomer@example.com",
            "password": "a-long-enough-password",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
        headers=csrf_headers,
    )

    assert response.status_code == 200
    message = sent_message(mail_stub)
    assert recipients(message) == ["newcomer@example.com"]
    assert decoded_subject(message) == (
        "VISIT: E-Mail-Adresse bestätigen / VISIT: Confirm your email address"
    )


async def test_failed_confirm_email_mail_does_not_keep_the_registration(
    client: AsyncClient, csrf_headers: dict[str, str], mail_stub: AsyncMock
):
    payload = {
        "email": "unlucky@example.com",
        "password": "a-long-enough-password",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }
    mail_stub.SendMail.side_effect = RuntimeError("notifications api down")

    failed = await client.post("/api/auth/register", json=payload, headers=csrf_headers)
    assert failed.status_code == 503
    assert failed.json()["code"] == "error.mail_unavailable"

    mail_stub.SendMail.side_effect = None
    response = await client.post(
        "/api/auth/register", json=payload, headers=csrf_headers
    )

    assert response.status_code == 200


async def test_password_reset_request_sends_the_reset_mail(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    mail_stub: AsyncMock,
):
    response = await client.post(
        "/api/auth/reset-password",
        json={"email": company_user.email},
        headers=csrf_headers,
    )

    assert response.status_code == 200
    message = sent_message(mail_stub)
    assert recipients(message) == [company_user.email]
    assert decoded_subject(message) == (
        "VISIT: Passwort zurücksetzen / VISIT: Reset your password"
    )


async def test_company_invite_sends_the_invite_mail(
    client: AsyncClient, company_headers: dict[str, str], mail_stub: AsyncMock
):
    response = await client.post(
        "/api/company/invite",
        json={"email": "guest@example.com"},
        headers=company_headers,
    )

    assert response.status_code == 200
    message = sent_message(mail_stub)
    assert recipients(message) == ["guest@example.com"]
    assert decoded_subject(message) == (
        "VISIT: Einladung zu Acme AG / VISIT: Invitation to join Acme AG"
    )


async def test_email_confirmation_notifies_the_staff_address(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    unconfirmed_company_user: User,
    mail_stub: AsyncMock,
):
    token = await auth_service.create_confirm_email_token(unconfirmed_company_user)

    response = await client.post(
        f"/api/user/confirm-email/{token}", headers=csrf_headers
    )

    assert response.status_code == 200
    message = sent_message(mail_stub)
    assert recipients(message) == ["kontaktparty@vis.ethz.ch"]
    assert decoded_subject(message) == (
        "VISIT: Neues Konto wartet auf Freigabe / VISIT: New account awaiting approval"
    )


async def test_staff_confirmation_sends_the_account_confirmed_mail(
    client: AsyncClient,
    staff_headers: dict[str, str],
    unconfirmed_company_user: User,
    mail_stub: AsyncMock,
):
    response = await client.post(
        f"/api/users/{unconfirmed_company_user.id}/confirm", headers=staff_headers
    )

    assert response.status_code == 200
    message = sent_message(mail_stub)
    assert recipients(message) == [unconfirmed_company_user.email]
    assert decoded_subject(message) == (
        "VISIT: Konto freigeschaltet / VISIT: Account activated"
    )
    assert "/auth/link/" in getattr(message, "plain_text")


async def test_staff_confirmation_of_a_staff_user_sends_nothing(
    client: AsyncClient,
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    mail_stub: AsyncMock,
):
    colleague = await create_user(
        email="colleague@example.com",
        is_staff=True,
        is_company=False,
        user_confirmed=False,
    )

    response = await client.post(
        f"/api/users/{colleague.id}/confirm", headers=staff_headers
    )

    assert response.status_code == 200
    mail_stub.SendMail.assert_not_awaited()


async def test_confirming_through_the_user_editor_sends_the_account_confirmed_mail(
    client: AsyncClient,
    staff_headers: dict[str, str],
    unconfirmed_company_user: User,
    mail_stub: AsyncMock,
):
    response = await client.patch(
        f"/api/users/{unconfirmed_company_user.id}",
        json={"user_confirmed": True},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["user_confirmed"] is True
    message = sent_message(mail_stub)
    assert recipients(message) == [unconfirmed_company_user.email]
    assert getattr(message, "subject") == (
        "VISIT: Konto freigeschaltet / VISIT: Account activated"
    )


async def test_editing_a_confirmed_user_sends_no_account_confirmed_mail(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    mail_stub: AsyncMock,
):
    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"user_confirmed": True, "first_name": "Renamed"},
        headers=staff_headers,
    )

    assert response.status_code == 200
    mail_stub.SendMail.assert_not_awaited()


async def test_confirming_twice_sends_the_mail_once(
    client: AsyncClient,
    staff_headers: dict[str, str],
    unconfirmed_company_user: User,
    mail_stub: AsyncMock,
):
    confirm_url = f"/api/users/{unconfirmed_company_user.id}/confirm"

    await client.post(confirm_url, headers=staff_headers)
    await client.post(confirm_url, headers=staff_headers)

    mail_stub.SendMail.assert_awaited_once()


async def test_a_failed_account_confirmed_mail_keeps_the_confirmation(
    client: AsyncClient,
    staff_headers: dict[str, str],
    unconfirmed_company_user: User,
    mail_stub: AsyncMock,
    caplog: pytest.LogCaptureFixture,
):
    mail_stub.SendMail.side_effect = RuntimeError("notifications api down")

    response = await client.post(
        f"/api/users/{unconfirmed_company_user.id}/confirm", headers=staff_headers
    )
    user = await client.get(
        f"/api/users/{unconfirmed_company_user.id}", headers=staff_headers
    )

    assert response.status_code == 200
    assert user.json()["user_confirmed"] is True
    assert any(
        record.levelname == "ERROR"
        and unconfirmed_company_user.email in record.getMessage()
        for record in caplog.records
    )
