import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.company import CompanyInvite
from app.models.user import User

INVITED_EMAIL = "invitee@example.com"
INVITED_PASSWORD = "invited-password-1"


def register_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "email": INVITED_EMAIL,
        "password": INVITED_PASSWORD,
        "first_name": "Ada",
        "last_name": "Lovelace",
        **overrides,
    }


def mail_text(message: Any) -> str:
    return message.plain_text


def sent_links(mail_stub: AsyncMock, marker: str) -> list[str]:
    pattern = re.compile(re.escape(marker) + r"([^\s)]+)")
    return [
        match
        for call in mail_stub.SendMail.await_args_list
        for match in pattern.findall(mail_text(call.args[0]))
    ]


async def invite_link(
    client: AsyncClient,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
    email: str = INVITED_EMAIL,
) -> str:
    await client.post(
        "/api/company/invite", json={"email": email}, headers=company_headers
    )
    return sent_links(mail_stub, "/company/join/")[-1]


async def create_invite(
    client: AsyncClient,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
    email: str = INVITED_EMAIL,
) -> str:
    return (await invite_link(client, company_headers, mail_stub, email)).split("?")[0]


async def expire_invite(db_session: AsyncSession, token: str) -> None:
    statement = select(CompanyInvite).where(col(CompanyInvite.token) == token)
    invite = (await db_session.execute(statement)).scalar_one()
    invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.add(invite)
    await db_session.commit()


async def confirm_registered_email(
    client: AsyncClient, csrf_headers: dict[str, str], mail_stub: AsyncMock
) -> None:
    token = sent_links(mail_stub, "/confirm-email/")[-1]
    await client.post(f"/api/user/confirm-email/{token}", headers=csrf_headers)


async def company_of(
    client: AsyncClient, staff_headers: dict[str, str], email: str
) -> str | None:
    response = await client.get(f"/api/users?query={email}", headers=staff_headers)
    company = response.json()["items"][0]["company"]
    return company["name"] if company else None


@pytest.fixture
async def invite_token(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
) -> str:
    return await create_invite(client, company_headers, mail_stub)


async def test_invite_mail_link_prefills_the_invited_email(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    link = await invite_link(
        client, company_headers, mail_stub, email="a+b@example.com"
    )

    token, query = link.split("?")
    assert token
    assert query == "email=a%2Bb%40example.com"


async def test_invite_info_does_not_leak_the_invited_email(
    client: AsyncClient, invite_token: str
):
    response = await client.get(f"/api/company/invite/{invite_token}")

    assert "email" not in response.json()


async def test_invite_info_is_public_and_reports_a_missing_account(
    client: AsyncClient, invite_token: str
):
    response = await client.get(f"/api/company/invite/{invite_token}")

    assert response.status_code == 200
    assert response.json() == {"company_name": "Acme AG", "account_exists": False}


async def test_invite_info_reports_an_existing_account(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    mail_stub: AsyncMock,
):
    await create_user(email=INVITED_EMAIL, password=None)
    token = await create_invite(client, company_headers, mail_stub)

    response = await client.get(f"/api/company/invite/{token}")

    assert response.status_code == 200
    assert response.json()["account_exists"] is True


async def test_invite_info_rejects_an_expired_token(
    client: AsyncClient, db_session: AsyncSession, invite_token: str
):
    await expire_invite(db_session, invite_token)

    response = await client.get(f"/api/company/invite/{invite_token}")

    assert response.status_code == 400
    assert response.json()["code"] == "error.invite_expired"


async def test_invite_info_rejects_an_unknown_token(client: AsyncClient):
    response = await client.get("/api/company/invite/not-a-token")

    assert response.status_code == 404
    assert response.json()["code"] == "error.invite_not_found"


async def test_registration_with_an_invite_joins_after_confirmation(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    staff_headers: dict[str, str],
    invite_token: str,
    mail_stub: AsyncMock,
):
    registration = await client.post(
        "/api/auth/register",
        json=register_payload(invite_token=invite_token),
        headers=csrf_headers,
    )
    before = await company_of(client, staff_headers, INVITED_EMAIL)
    await confirm_registered_email(client, csrf_headers, mail_stub)

    assert registration.status_code == 200
    assert before is None
    assert await company_of(client, staff_headers, INVITED_EMAIL) == "Acme AG"


async def test_an_applied_invite_cannot_be_used_twice(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    invite_token: str,
    mail_stub: AsyncMock,
):
    await client.post(
        "/api/auth/register",
        json=register_payload(invite_token=invite_token),
        headers=csrf_headers,
    )
    await confirm_registered_email(client, csrf_headers, mail_stub)

    response = await client.get(f"/api/company/invite/{invite_token}")

    assert response.status_code == 404
    assert response.json()["code"] == "error.invite_not_found"


async def test_registration_rejects_an_invite_for_another_email(
    client: AsyncClient, csrf_headers: dict[str, str], invite_token: str
):
    response = await client.post(
        "/api/auth/register",
        json=register_payload(
            email="someone-else@example.com", invite_token=invite_token
        ),
        headers=csrf_headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.invite_email_mismatch"


async def test_registration_rejects_an_expired_invite(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    db_session: AsyncSession,
    invite_token: str,
):
    await expire_invite(db_session, invite_token)

    response = await client.post(
        "/api/auth/register",
        json=register_payload(invite_token=invite_token),
        headers=csrf_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.invite_expired"


async def test_registration_rejects_an_unknown_invite(
    client: AsyncClient, csrf_headers: dict[str, str]
):
    response = await client.post(
        "/api/auth/register",
        json=register_payload(invite_token="not-a-token"),
        headers=csrf_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.invite_not_found"


async def test_confirmation_succeeds_when_the_invite_expired_meanwhile(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    staff_headers: dict[str, str],
    db_session: AsyncSession,
    invite_token: str,
    mail_stub: AsyncMock,
):
    await client.post(
        "/api/auth/register",
        json=register_payload(invite_token=invite_token),
        headers=csrf_headers,
    )
    await expire_invite(db_session, invite_token)
    token = sent_links(mail_stub, "/confirm-email/")[-1]

    response = await client.post(
        f"/api/user/confirm-email/{token}", headers=csrf_headers
    )

    assert response.status_code == 200
    assert await company_of(client, staff_headers, INVITED_EMAIL) is None


async def test_registration_without_an_invite_stays_company_less(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    staff_headers: dict[str, str],
    company_user: User,
    mail_stub: AsyncMock,
):
    await client.post(
        "/api/auth/register", json=register_payload(), headers=csrf_headers
    )
    await confirm_registered_email(client, csrf_headers, mail_stub)

    assert await company_of(client, staff_headers, INVITED_EMAIL) is None
