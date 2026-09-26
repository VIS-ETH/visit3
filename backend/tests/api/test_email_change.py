import re
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import grpc
import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from tests.api.conftest import DEFAULT_PASSWORD, decoded_subject

NEW_EMAIL = "moved@example.com"


class MailRpcError(grpc.RpcError):
    pass


def recipients(message: object) -> list[str]:
    return [address.mail_address.address for address in getattr(message, "to")]


def mails_to(mail_stub: AsyncMock, email: str) -> list[object]:
    return [
        call.args[0]
        for call in mail_stub.SendMail.await_args_list
        if recipients(call.args[0]) == [email]
    ]


def confirm_token(mail_stub: AsyncMock, email: str = NEW_EMAIL) -> str:
    message = str(mails_to(mail_stub, email)[-1])
    return re.findall(r"/confirm-email/([A-Za-z0-9_-]+)", message)[-1]


async def change_email(
    client: AsyncClient, user: User, headers: dict[str, str], email: str = NEW_EMAIL
) -> Response:
    return await client.patch(
        f"/api/users/{user.id}", json={"email": email}, headers=headers
    )


async def login(
    client: AsyncClient, csrf_headers: dict[str, str], email: str
) -> Response:
    return await client.post(
        "/api/auth/login",
        data={"username": email, "password": DEFAULT_PASSWORD},
        headers=csrf_headers,
    )


async def stored(db_session: AsyncSession, user: User) -> User:
    loaded = await UserRepository(db_session).get_by_id(user.id)
    assert loaded is not None
    await db_session.refresh(loaded)
    return loaded


@pytest.fixture
async def plain_staff_headers(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    helper = await create_user(
        email="helper@example.com", is_staff=True, is_company=False
    )
    return {**await auth_headers(helper), **csrf_headers}


async def test_an_email_change_waits_for_the_new_address(
    client: AsyncClient,
    company_user: User,
    plain_staff_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
):
    old_email = company_user.email

    response = await change_email(client, company_user, plain_staff_headers)

    assert response.status_code == 200
    assert response.json()["email"] == old_email
    assert response.json()["pending_email"] == NEW_EMAIL
    user = await stored(db_session, company_user)
    assert user.email == old_email
    assert user.email_confirmed is True
    assert decoded_subject(mails_to(mail_stub, NEW_EMAIL)[0]) == (
        "VISIT: Neue E-Mail-Adresse bestätigen / VISIT: Confirm your new email address"
    )
    notice = mails_to(mail_stub, old_email)[0]
    assert decoded_subject(notice) == (
        "VISIT: Ihre E-Mail-Adresse soll geändert werden"
        " / VISIT: Your email address is being changed"
    )
    assert NEW_EMAIL in str(notice)


async def test_the_old_address_keeps_working_until_the_change_is_confirmed(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    plain_staff_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
):
    session = (await login(client, csrf_headers, company_user.email)).cookies[
        "refresh_token"
    ]
    await change_email(client, company_user, plain_staff_headers)
    reset = await client.post(
        "/api/auth/reset-password", json={"email": NEW_EMAIL}, headers=csrf_headers
    )

    client.cookies.set("refresh_token", session)
    still_logged_in = await client.post("/api/auth/refresh", headers=csrf_headers)
    old_login = await login(client, csrf_headers, company_user.email)

    assert reset.status_code == 200
    assert mails_to(mail_stub, NEW_EMAIL) and all(
        "/reset/" not in str(message) for message in mails_to(mail_stub, NEW_EMAIL)
    )
    assert still_logged_in.status_code == 200
    assert old_login.status_code == 200


async def test_confirming_the_new_address_switches_the_email_and_ends_sessions(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    plain_staff_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
):
    session = (await login(client, csrf_headers, company_user.email)).cookies[
        "refresh_token"
    ]
    await change_email(client, company_user, plain_staff_headers)
    token = confirm_token(mail_stub)

    valid = await client.get(f"/api/user/confirm-email/{token}")
    confirmed = await client.post(
        f"/api/user/confirm-email/{token}", headers=csrf_headers
    )
    client.cookies.set("refresh_token", session)
    old_session = await client.post("/api/auth/refresh", headers=csrf_headers)
    new_login = await login(client, csrf_headers, NEW_EMAIL)
    replay = await client.post(f"/api/user/confirm-email/{token}", headers=csrf_headers)

    assert valid.json() is True
    assert confirmed.status_code == 200
    user = await stored(db_session, company_user)
    assert user.email == NEW_EMAIL
    assert user.email_confirmed is True
    assert user.pending_email is None
    assert old_session.status_code == 401
    assert new_login.status_code == 200
    assert replay.status_code == 400


async def test_a_newer_change_request_invalidates_the_older_link(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    plain_staff_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
):
    await change_email(client, company_user, plain_staff_headers)
    first = confirm_token(mail_stub)
    await change_email(client, company_user, plain_staff_headers, "second@example.com")

    stale = await client.post(f"/api/user/confirm-email/{first}", headers=csrf_headers)

    assert stale.status_code == 400
    user = await stored(db_session, company_user)
    assert user.email == company_user.email
    assert user.pending_email == "second@example.com"


async def test_confirming_fails_when_the_address_was_taken_meanwhile(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    plain_staff_headers: dict[str, str],
    mail_stub: AsyncMock,
    create_user: Callable[..., Awaitable[User]],
    db_session: AsyncSession,
):
    await change_email(client, company_user, plain_staff_headers)
    token = confirm_token(mail_stub)
    await create_user(email=NEW_EMAIL)

    response = await client.post(
        f"/api/user/confirm-email/{token}", headers=csrf_headers
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.email_used"
    assert (await stored(db_session, company_user)).email == company_user.email


async def test_an_unavailable_mail_service_leaves_nothing_pending(
    client: AsyncClient,
    company_user: User,
    plain_staff_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
):
    mail_stub.SendMail.side_effect = MailRpcError()

    response = await change_email(client, company_user, plain_staff_headers)

    assert response.status_code == 503
    assert (await stored(db_session, company_user)).pending_email is None


async def test_an_admin_email_change_for_staff_uses_the_same_confirmation(
    client: AsyncClient,
    staff_user: User,
    staff_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    response = await change_email(
        client, staff_user, staff_headers, "new-staff@example.com"
    )

    assert response.status_code == 200
    assert response.json()["email"] == staff_user.email
    assert response.json()["pending_email"] == "new-staff@example.com"
    assert mails_to(mail_stub, "new-staff@example.com")
