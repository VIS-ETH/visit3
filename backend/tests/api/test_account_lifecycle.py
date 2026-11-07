import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, update

from app.models.user import User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository

MAX_AGE = timedelta(days=7)


async def age(db_session: AsyncSession, user: User, days: int) -> None:
    await db_session.execute(
        update(User)
        .where(col(User.id) == user.id)
        .values(created_at=datetime.now(timezone.utc) - timedelta(days=days))
    )
    await db_session.commit()


@pytest.mark.parametrize(
    "privileges", [{"is_staff": True}, {"is_staff": True, "is_admin": True}]
)
async def test_unconfirmed_staff_accounts_are_not_purged(
    db_session: AsyncSession,
    create_user: Callable[..., Awaitable[User]],
    privileges: dict[str, bool],
):
    staff = await create_user(
        email="staff@example.com",
        is_company=False,
        email_confirmed=False,
        **privileges,
    )
    await age(db_session, staff, 8)

    purged = await UserRepository(db_session).purge_unconfirmed_accounts(MAX_AGE)

    assert purged == 0


async def test_unconfirmed_company_accounts_are_still_purged(
    db_session: AsyncSession, create_user: Callable[..., Awaitable[User]]
):
    user = await create_user(email="stale@example.com", email_confirmed=False)
    await age(db_session, user, 8)

    purged = await UserRepository(db_session).purge_unconfirmed_accounts(MAX_AGE)

    assert purged == 1


async def test_a_password_reset_confirms_the_email_address(
    client: AsyncClient,
    db_session: AsyncSession,
    csrf_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
):
    user = await create_user(email="unconfirmed@example.com", email_confirmed=False)
    token = await TokenRepository(db_session).create_reset_password_token(user.id)

    response = await client.post(
        "/api/auth/reset",
        json={"token": token, "new_password": "another-password-1"},
        headers=csrf_headers,
    )

    assert response.status_code == 200, response.text
    await db_session.refresh(user)
    assert user.email_confirmed is True


async def test_a_pending_invite_does_not_move_a_member_assigned_by_staff(
    client: AsyncClient,
    db_session: AsyncSession,
    csrf_headers: dict[str, str],
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    mail_stub: AsyncMock,
):
    invited = await client.post(
        "/api/company/invite",
        json={"email": "newbie@example.com"},
        headers=company_headers,
    )
    assert invited.status_code == 200, invited.text
    match = re.search(r"company/join/([A-Za-z0-9_\-]+)", str(mail_stub.mock_calls))
    assert match is not None
    registered = await client.post(
        "/api/auth/register",
        json={
            "email": "newbie@example.com",
            "password": "newbie-password",
            "first_name": "New",
            "last_name": "Bie",
            "invite_token": match.group(1),
        },
        headers=csrf_headers,
    )
    assert registered.status_code == 200, registered.text
    newbie = await UserRepository(db_session).get_by_email("newbie@example.com")
    assert newbie is not None
    other = await create_user(email="other@example.com", company_name="Other AG")
    added = await client.post(
        f"/api/companies/{other.company_id}/members",
        json={"user_id": str(newbie.id)},
        headers=staff_headers,
    )
    assert added.status_code == 200, added.text
    token = await TokenRepository(db_session).create_confirm_email_token(newbie.id)

    confirmed = await client.post(
        f"/api/user/confirm-email/{token}", headers=csrf_headers
    )

    assert confirmed.status_code == 200, confirmed.text
    await db_session.refresh(newbie)
    assert newbie.company_id == other.company_id
