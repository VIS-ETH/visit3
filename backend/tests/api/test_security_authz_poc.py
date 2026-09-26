import re
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select, update

from app.core.config import get_settings
from app.core.exceptions import NotVisMember
from app.core.utils import hash_str
from app.models.company import CompanyInvite
from app.models.user import RefreshToken, User
from app.repositories.token_repository import REFRESH_TOKEN_REUSE_GRACE
from app.services import auth_service as auth_module
from app.services.auth_service import AuthService
from tests.api.conftest import DEFAULT_PASSWORD

ATTEMPTS_OVER_LIMIT = get_settings().RATE_LIMIT_MAX_REQUESTS + 1
ALT_EMAIL = "former.member.private@example.com"
NEW_STAFF_EMAIL = "new.board.member@example.com"


def keycloak_claims(
    email: str, roles: Sequence[str] = ("vis-active",), sub: str | None = None
) -> dict[str, Any]:
    return {
        "sub": sub or str(uuid4()),
        "email": email,
        "given_name": "Grace",
        "family_name": "Hopper",
        "resource_access": {
            get_settings().SIP_AUTH_OIDC_CLIENT_ID: {"roles": list(roles)}
        },
    }


async def login(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    email: str,
    password: str = DEFAULT_PASSWORD,
) -> Response:
    return await client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers=csrf_headers,
    )


async def refresh(
    client: AsyncClient, csrf_headers: dict[str, str], refresh_token: str
) -> Response:
    client.cookies.set("refresh_token", refresh_token)
    return await client.post("/api/auth/refresh", headers=csrf_headers)


def sent_invite_tokens(mail_stub: AsyncMock) -> list[str]:
    return [
        token
        for call in mail_stub.SendMail.await_args_list
        for token in re.findall(r"/company/join/([A-Za-z0-9_-]+)", str(call.args[0]))
    ]


async def test_poc_offboarded_keycloak_staff_keeps_access_through_refresh(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
):
    claims = keycloak_claims("leaving.member@example.com", roles=("vis-active",))
    refresh_token = await auth_service.login_keycloak_user(claims)
    with pytest.raises(NotVisMember):
        await auth_service.login_keycloak_user({**claims, "resource_access": {}})

    response = await refresh(client, csrf_headers, refresh_token)

    assert response.status_code == 401


async def test_poc_login_is_not_rate_limited(
    client: AsyncClient, csrf_headers: dict[str, str], company_user: User
):
    responses = [
        await login(client, csrf_headers, company_user.email, "wrong-password")
        for _ in range(ATTEMPTS_OVER_LIMIT)
    ]

    assert responses[-1].status_code == 429


async def test_poc_registration_is_not_rate_limited(
    client: AsyncClient, csrf_headers: dict[str, str], mail_stub: AsyncMock
):
    responses = [
        await client.post(
            "/api/auth/register",
            json={
                "email": f"victim{index}@example.com",
                "password": "long-enough-password",
                "first_name": "Spam",
                "last_name": "Target",
            },
            headers=csrf_headers,
        )
        for index in range(ATTEMPTS_OVER_LIMIT)
    ]

    assert responses[-1].status_code == 429
    assert mail_stub.SendMail.await_count < ATTEMPTS_OVER_LIMIT


async def test_poc_invite_created_by_a_removed_member_still_joins_the_company(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    csrf_headers: dict[str, str],
    mail_stub: AsyncMock,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
):
    await client.post(
        "/api/company/invite", json={"email": ALT_EMAIL}, headers=company_headers
    )
    token = sent_invite_tokens(mail_stub)[-1]
    removed = await client.delete(
        f"/api/companies/{company_user.company_id}/members/{company_user.id}",
        headers=staff_headers,
    )
    alt_account = await create_user(email=ALT_EMAIL)

    response = await client.post(
        f"/api/company/invite/{token}/accept",
        headers={**await auth_headers(alt_account), **csrf_headers},
    )

    assert removed.status_code == 200
    assert response.status_code != 200


async def test_poc_debug_keycloak_admin_makes_any_sso_account_admin_outside_debug(
    auth_service: AuthService,
    monkeypatch: pytest.MonkeyPatch,
):
    settings = get_settings()
    assert settings.DEBUG is False
    monkeypatch.setattr(settings, "DEBUG_KEYCLOAK_ADMIN", True)

    with pytest.raises(NotVisMember):
        await auth_service.login_keycloak_user(
            keycloak_claims("any.student@example.com", roles=())
        )


async def test_poc_unconfirmed_registration_blocks_the_first_sso_login(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
):
    squatted = await client.post(
        "/api/auth/register",
        json={
            "email": NEW_STAFF_EMAIL,
            "password": "long-enough-password",
            "first_name": "Not",
            "last_name": "Them",
        },
        headers=csrf_headers,
    )

    refresh_token = await auth_service.login_keycloak_user(
        keycloak_claims(NEW_STAFF_EMAIL)
    )

    assert squatted.status_code == 200
    assert refresh_token


async def test_poc_login_link_survives_a_mail_scanner_but_not_a_fourth_use(
    client: AsyncClient,
    company_user: User,
    auth_service: AuthService,
):
    link = await auth_service.create_login_link(company_user, "/")
    token = link.rsplit("/", 1)[-1]

    scanner = await client.get(f"/api/auth/link/{token}")
    owner = await client.get(f"/api/auth/link/{token}")
    await client.get(f"/api/auth/link/{token}")
    replay = await client.get(f"/api/auth/link/{token}")

    assert scanner.status_code == owner.status_code == 303
    assert owner.cookies.get("refresh_token")
    assert "refresh_token" not in replay.headers.get("set-cookie", "")


async def test_poc_reusing_a_rotated_refresh_token_does_not_end_the_session(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    db_session: AsyncSession,
):
    stolen = (await login(client, csrf_headers, company_user.email)).cookies[
        "refresh_token"
    ]
    rotated = (await refresh(client, csrf_headers, stolen)).cookies["refresh_token"]
    await db_session.execute(
        update(RefreshToken)
        .where(col(RefreshToken.token) == hash_str(stolen))
        .values(rotated_at=datetime.now(timezone.utc) - REFRESH_TOKEN_REUSE_GRACE * 2)
    )
    await db_session.commit()

    reuse = await refresh(client, csrf_headers, stolen)
    follow_up = await refresh(client, csrf_headers, rotated)

    assert reuse.status_code == 401
    assert follow_up.status_code == 401


async def test_poc_login_skips_password_hashing_for_unknown_emails(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    company_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    verified: list[str] = []
    original = auth_module.password_hash.verify_and_update

    def counting(password: str, hashed: str) -> tuple[bool, str | None]:
        verified.append(password)
        return original(password, hashed)

    monkeypatch.setattr(auth_module.password_hash, "verify_and_update", counting)

    await login(client, csrf_headers, company_user.email, "wrong-password-1")
    known = len(verified)
    await login(client, csrf_headers, "nobody@example.com", "wrong-password-2")
    unknown = len(verified) - known

    assert unknown == known


async def test_poc_plain_staff_can_redirect_a_company_account_email(
    client: AsyncClient,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    helper = await create_user(
        email="helper@example.com", is_staff=True, is_company=False
    )

    response = await client.patch(
        f"/api/users/{company_user.id}",
        json={"email": "helper.private@example.com"},
        headers={**await auth_headers(helper), **csrf_headers},
    )

    assert response.status_code == 403


async def test_poc_invite_tokens_are_stored_in_plain_text(
    client: AsyncClient,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
    db_session: AsyncSession,
):
    await client.post(
        "/api/company/invite",
        json={"email": "colleague@example.com"},
        headers=company_headers,
    )
    token = sent_invite_tokens(mail_stub)[-1]

    stored = (
        await db_session.execute(
            select(CompanyInvite).where(col(CompanyInvite.token) == token)
        )
    ).scalar_one_or_none()

    assert stored is None
