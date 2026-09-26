import re
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.utils import hash_str
from app.models.company import CompanyInvite
from app.models.user import User

COMPANY = "Invite AG"


def last_invite_token(mail_stub: AsyncMock) -> str:
    message = str(mail_stub.SendMail.await_args.args[0])
    return re.findall(r"/company/join/([A-Za-z0-9_-]+)", message)[-1]


async def invite(
    client: AsyncClient,
    headers: dict[str, str],
    mail_stub: AsyncMock,
    email: str,
) -> str:
    response = await client.post(
        "/api/company/invite", json={"email": email}, headers=headers
    )
    assert response.status_code == 200
    return last_invite_token(mail_stub)


async def accept(
    client: AsyncClient,
    token: str,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    email: str,
) -> Response:
    account = await create_user(email=email)
    return await client.post(
        f"/api/company/invite/{token}/accept",
        headers={**await auth_headers(account), **csrf_headers},
    )


async def two_members(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    db_session: AsyncSession,
) -> tuple[User, dict[str, str], User, dict[str, str]]:
    leaver = await create_user(email="leaver@example.com", company_name=COMPANY)
    stayer = await create_user(email="stayer@example.com")
    stayer.company_id = leaver.company_id
    db_session.add(stayer)
    await db_session.commit()
    return (
        leaver,
        {**await auth_headers(leaver), **csrf_headers},
        stayer,
        {**await auth_headers(stayer), **csrf_headers},
    )


async def test_an_invite_remembers_who_sent_it_and_stores_only_a_hash(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
):
    token = await invite(client, company_headers, mail_stub, "guest@example.com")

    stored = (
        await db_session.execute(
            select(CompanyInvite).where(col(CompanyInvite.token) == hash_str(token))
        )
    ).scalar_one()
    assert stored.invited_by_user_id == company_user.id


async def test_removing_a_member_revokes_only_their_invites(
    client: AsyncClient,
    staff_headers: dict[str, str],
    csrf_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    leaver, leaver_headers, _, stayer_headers = await two_members(
        create_user, auth_headers, csrf_headers, db_session
    )
    leaver_invite = await invite(client, leaver_headers, mail_stub, "alt@example.com")
    stayer_invite = await invite(client, stayer_headers, mail_stub, "new@example.com")

    await client.delete(
        f"/api/companies/{leaver.company_id}/members/{leaver.id}",
        headers=staff_headers,
    )

    revoked = await accept(
        client,
        leaver_invite,
        create_user,
        auth_headers,
        csrf_headers,
        "alt@example.com",
    )
    kept = await accept(
        client,
        stayer_invite,
        create_user,
        auth_headers,
        csrf_headers,
        "new@example.com",
    )
    assert revoked.status_code == 404
    assert kept.status_code == 200


async def test_moving_a_member_to_another_company_revokes_their_invites(
    client: AsyncClient,
    staff_headers: dict[str, str],
    csrf_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    leaver, leaver_headers, _, _ = await two_members(
        create_user, auth_headers, csrf_headers, db_session
    )
    token = await invite(client, leaver_headers, mail_stub, "alt@example.com")
    other = await create_user(email="other@example.com", company_name="Other AG")

    moved = await client.patch(
        f"/api/users/{leaver.id}",
        json={"company_id": str(other.company_id)},
        headers=staff_headers,
    )

    response = await accept(
        client, token, create_user, auth_headers, csrf_headers, "alt@example.com"
    )
    assert moved.status_code == 200
    assert response.status_code == 404


async def test_deleting_a_member_revokes_their_invites(
    client: AsyncClient,
    staff_headers: dict[str, str],
    csrf_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    leaver, leaver_headers, _, _ = await two_members(
        create_user, auth_headers, csrf_headers, db_session
    )
    token = await invite(client, leaver_headers, mail_stub, "alt@example.com")

    deleted = await client.delete(f"/api/users/{leaver.id}", headers=staff_headers)

    response = await accept(
        client, token, create_user, auth_headers, csrf_headers, "alt@example.com"
    )
    assert deleted.status_code == 200
    assert response.status_code == 404
