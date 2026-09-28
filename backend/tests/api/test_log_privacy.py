import logging

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.api.conftest import DEFAULT_PASSWORD

NEW_EMAIL = "brand-new@example.com"


@pytest.fixture
def captured(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.DEBUG, logger="app")
    return caplog


def _messages(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


async def test_login_and_logout_log_the_user_id_not_the_email(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    captured: pytest.LogCaptureFixture,
):
    await client.post(
        "/api/auth/login",
        data={"username": company_user.email, "password": "wrong-password"},
        headers=csrf_headers,
    )
    login = await client.post(
        "/api/auth/login",
        data={"username": company_user.email, "password": DEFAULT_PASSWORD},
        headers=csrf_headers,
    )
    token = login.json()["access_token"]
    await client.post(
        "/api/user/logout",
        headers={**csrf_headers, "Authorization": f"Bearer {token}"},
    )

    messages = _messages(captured)
    assert company_user.email not in messages
    assert str(company_user.id) in messages


async def test_registration_and_reset_requests_do_not_log_emails(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    captured: pytest.LogCaptureFixture,
):
    await client.post(
        "/api/auth/register",
        json={
            "email": NEW_EMAIL,
            "password": "brand-new-password",
            "first_name": "New",
            "last_name": "Company",
        },
        headers=csrf_headers,
    )
    for email in (company_user.email, "nobody@example.com"):
        await client.post(
            "/api/auth/reset-password", json={"email": email}, headers=csrf_headers
        )

    messages = _messages(captured)
    assert "@" not in messages


async def test_impersonation_logs_both_user_ids(
    client: AsyncClient,
    company_user: User,
    admin_user: User,
    staff_headers: dict[str, str],
    captured: pytest.LogCaptureFixture,
):
    await client.get(
        "/api/user/me",
        headers={**staff_headers, "X-Impersonate-User-Id": str(company_user.id)},
    )

    messages = _messages(captured)
    assert "@" not in messages
    assert str(admin_user.id) in messages
    assert str(company_user.id) in messages
