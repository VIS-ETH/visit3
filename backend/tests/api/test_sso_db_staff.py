from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import EmailTakenLocally, EmailUsed, NotVisMember
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from tests.api.test_sso_sessions import (
    EMAIL,
    SUB,
    FakeKeycloak,
    active_tokens,
    claims,
    keycloak,
    refresh,
    sso_user,
)

__all__ = ["keycloak"]


@pytest.fixture(autouse=True)
def roles_not_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "KEYCLOAK_REQUIRE_ROLES", False)


async def stored_user(
    db_session: AsyncSession, *, is_staff: bool, is_admin: bool, is_company: bool
) -> User:
    user = User(
        email=EMAIL,
        sub=SUB,
        first_name="Old",
        last_name="Name",
        is_staff=is_staff,
        is_admin=is_admin,
        is_company=is_company,
        user_confirmed=True,
        email_confirmed=True,
    )
    roles = [await RoleRepository(db_session).get_or_create("vis-active")]
    return await UserRepository(db_session).create_user(user, roles)


async def test_an_existing_staff_member_logs_in_without_keycloak_roles(
    auth_service: AuthService, db_session: AsyncSession
):
    await stored_user(db_session, is_staff=True, is_admin=False, is_company=False)

    refresh_token = await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    user = await sso_user(db_session)
    assert refresh_token
    assert user.is_staff is True
    assert user.is_admin is False
    assert [role.name for role in user.roles] == ["vis-active"]
    assert (user.first_name, user.last_name) == ("Grace", "Hopper")


async def test_an_existing_admin_keeps_admin_rights(
    auth_service: AuthService, db_session: AsyncSession
):
    await stored_user(db_session, is_staff=True, is_admin=True, is_company=False)

    await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    user = await sso_user(db_session)
    assert user.is_admin is True
    assert user.is_staff is True


def rights(user: User) -> tuple[bool, bool, bool, bool]:
    return (user.is_staff, user.is_admin, user.is_company, user.is_kp_president)


NO_RIGHTS = (False, False, False, False)


async def test_an_unknown_member_logs_in_without_any_rights(
    auth_service: AuthService, db_session: AsyncSession
):
    refresh_token = await auth_service.login_keycloak_user(
        claims(("vis-active", "admin")), "kc-refresh-1"
    )

    user = await sso_user(db_session)
    assert refresh_token
    assert rights(user) == NO_RIGHTS
    assert user.roles == []
    assert (user.user_confirmed, user.email_confirmed) == (True, True)
    assert (user.first_name, user.last_name) == ("Grace", "Hopper")


async def test_an_account_without_rights_gains_none_from_the_token(
    auth_service: AuthService, db_session: AsyncSession
):
    await stored_user(db_session, is_staff=False, is_admin=False, is_company=False)

    await auth_service.login_keycloak_user(
        claims(("vis-active", "admin")), "kc-refresh-1"
    )

    user = await sso_user(db_session)
    assert rights(user) == NO_RIGHTS
    assert [role.name for role in user.roles] == ["vis-active"]


async def test_a_company_account_is_not_opened_through_sso(
    auth_service: AuthService, db_session: AsyncSession
):
    await stored_user(db_session, is_staff=False, is_admin=False, is_company=True)

    with pytest.raises(EmailTakenLocally):
        await auth_service.login_keycloak_user(claims(("vis-active",)), "kc-refresh-1")

    user = await sso_user(db_session)
    assert user.is_staff is False
    assert user.is_company is True


async def test_an_unconfirmed_local_account_is_replaced(
    auth_service: AuthService,
    create_user: Callable[..., Awaitable[User]],
    db_session: AsyncSession,
):
    local = await create_user(email=EMAIL, email_confirmed=False, user_confirmed=False)

    await auth_service.login_keycloak_user(claims(), "kc-refresh-1")

    user = await sso_user(db_session)
    assert user.id != local.id
    assert rights(user) == NO_RIGHTS


async def test_a_confirmed_local_account_keeps_its_email(
    auth_service: AuthService,
    create_user: Callable[..., Awaitable[User]],
    db_session: AsyncSession,
):
    await create_user(email=EMAIL)

    with pytest.raises(EmailTakenLocally):
        await auth_service.login_keycloak_user(claims(), "kc-refresh-1")

    assert await UserRepository(db_session).get_by_sub(SUB) is None


async def test_an_email_of_another_sso_account_is_refused(
    auth_service: AuthService,
    create_user: Callable[..., Awaitable[User]],
):
    await create_user(email=EMAIL, password=None, is_company=False)

    with pytest.raises(EmailUsed):
        await auth_service.login_keycloak_user(claims(), "kc-refresh-1")


async def test_a_refresh_keeps_the_stored_staff_rights(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
):
    await stored_user(db_session, is_staff=True, is_admin=True, is_company=False)
    keycloak.roles = ()
    refresh_token = await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    response = await refresh(client, csrf_headers, refresh_token)

    user = await sso_user(db_session)
    assert response.status_code == 200
    assert keycloak.requests[0]["grant_type"] == "refresh_token"
    assert user.is_staff is True
    assert user.is_admin is True
    assert await active_tokens(db_session, user) == 1


async def test_a_refresh_still_ends_when_keycloak_ended_the_session(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
):
    await stored_user(db_session, is_staff=True, is_admin=False, is_company=False)
    refresh_token = await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")
    keycloak.status = 400

    response = await refresh(client, csrf_headers, refresh_token)

    assert response.status_code == 401


async def test_a_refresh_keeps_a_demoted_account_without_rights(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
):
    user = await stored_user(db_session, is_staff=True, is_admin=True, is_company=False)
    refresh_token = await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")
    user.is_staff = False
    user.is_admin = False
    db_session.add(user)
    await db_session.commit()
    keycloak.roles = ("vis-active", "admin")

    response = await refresh(client, csrf_headers, refresh_token)

    demoted = await sso_user(db_session)
    assert response.status_code == 200
    assert (demoted.is_staff, demoted.is_admin) == (False, False)
    assert await active_tokens(db_session, demoted) == 1


async def test_a_new_member_refreshes_without_gaining_rights(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
):
    keycloak.roles = ("vis-active", "admin")
    refresh_token = await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    first = await refresh(client, csrf_headers, refresh_token)
    second = await refresh(client, csrf_headers, first.cookies["refresh_token"])

    user = await sso_user(db_session)
    assert first.status_code == second.status_code == 200
    assert rights(user) == NO_RIGHTS
    assert await active_tokens(db_session, user) == 1


async def test_an_admin_finds_a_new_member_and_grants_staff(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
):
    refresh_token = await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")
    member = await sso_user(db_session)

    listed = await client.get(
        "/api/users", params={"query": EMAIL}, headers=staff_headers
    )
    granted = await client.patch(
        f"/api/users/{member.id}", json={"is_staff": True}, headers=staff_headers
    )
    refreshed = await refresh(client, csrf_headers, refresh_token)
    await auth_service.login_keycloak_user(claims(()), "kc-refresh-9")

    user = await sso_user(db_session)
    assert [item["id"] for item in listed.json()["items"]] == [str(member.id)]
    assert granted.status_code == 200
    assert refreshed.status_code == 200
    assert (user.is_staff, user.is_admin, user.is_company) == (True, False, False)


async def test_plain_staff_cannot_grant_a_new_member_staff(
    client: AsyncClient,
    auth_service: AuthService,
    db_session: AsyncSession,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")
    member = await sso_user(db_session)
    staff = await create_user(
        email="plain.staff@example.com", is_staff=True, is_company=False
    )

    response = await client.patch(
        f"/api/users/{member.id}",
        json={"is_staff": True},
        headers={**await auth_headers(staff), **csrf_headers},
    )

    assert response.status_code == 403
    assert rights(await sso_user(db_session)) == NO_RIGHTS


async def test_a_new_member_cannot_grant_itself_rights(
    client: AsyncClient,
    auth_service: AuthService,
    db_session: AsyncSession,
    company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")
    member = await sso_user(db_session)

    await client.patch(
        "/api/user/me",
        json={
            "is_staff": True,
            "is_admin": True,
            "is_company": True,
            "company_id": str(company_user.company_id),
        },
        headers={**await auth_headers(member), **csrf_headers},
    )

    user = await sso_user(db_session)
    assert rights(user) == NO_RIGHTS
    assert user.company_id is None


async def test_a_new_member_cannot_become_a_company_user(
    client: AsyncClient,
    auth_service: AuthService,
    db_session: AsyncSession,
    company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")
    member = await sso_user(db_session)
    await CompanyRepository(db_session).create_invite(
        token="member-invite",
        company_id=UUID(str(company_user.company_id)),
        invited_email=EMAIL,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    headers = {**await auth_headers(member), **csrf_headers}

    setup = await client.post(
        "/api/company/setup", json={"name": "Member AG"}, headers=headers
    )
    accepted = await client.post(
        "/api/company/invite/member-invite/accept", headers=headers
    )

    user = await sso_user(db_session)
    assert setup.status_code == accepted.status_code == 403
    assert rights(user) == NO_RIGHTS
    assert user.company_id is None


def set_admin(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setattr(get_settings(), "SET_ADMIN", value)


async def test_set_admin_bootstraps_an_admin_into_an_empty_database(
    auth_service: AuthService,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    set_admin(monkeypatch, EMAIL)

    with caplog.at_level("INFO"):
        await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    user = await sso_user(db_session)
    assert user.is_admin is True
    assert user.is_staff is True
    grants = [record for record in caplog.records if "SET_ADMIN" in record.getMessage()]
    assert grants
    assert all(EMAIL not in record.getMessage() for record in grants)
    assert any(str(user.id) in record.getMessage() for record in grants)


async def test_set_admin_promotes_an_existing_non_staff_sso_user(
    auth_service: AuthService,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await stored_user(db_session, is_staff=False, is_admin=False, is_company=False)
    set_admin(monkeypatch, EMAIL)

    await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    user = await sso_user(db_session)
    assert user.is_admin is True
    assert user.is_staff is True


async def test_set_admin_matches_a_trimmed_case_insensitive_list(
    auth_service: AuthService,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    set_admin(monkeypatch, f" someone@example.com ,  {EMAIL.upper()} ")

    await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    assert (await sso_user(db_session)).is_admin is True


async def test_set_admin_leaves_other_emails_without_rights(
    auth_service: AuthService,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    set_admin(monkeypatch, "someone.else@example.com")

    await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    assert rights(await sso_user(db_session)) == NO_RIGHTS


async def test_set_admin_requires_a_verified_email_when_the_claim_is_present(
    auth_service: AuthService,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    set_admin(monkeypatch, EMAIL)

    await auth_service.login_keycloak_user(
        {**claims(()), "email_verified": False}, "kc-refresh-1"
    )

    assert rights(await sso_user(db_session)) == NO_RIGHTS


async def test_set_admin_never_takes_over_a_local_account(
    auth_service: AuthService,
    create_user: Callable[..., Awaitable[User]],
    monkeypatch: pytest.MonkeyPatch,
):
    await create_user(email=EMAIL)
    set_admin(monkeypatch, EMAIL)

    with pytest.raises(EmailTakenLocally):
        await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")


async def test_a_refresh_keeps_admin_for_a_set_admin_user(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    set_admin(monkeypatch, EMAIL)
    keycloak.roles = ()
    refresh_token = await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    response = await refresh(client, csrf_headers, refresh_token)

    user = await sso_user(db_session)
    assert response.status_code == 200
    assert user.is_admin is True


async def test_with_required_roles_set_admin_adds_to_the_token_roles(
    auth_service: AuthService,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(get_settings(), "KEYCLOAK_REQUIRE_ROLES", True)
    set_admin(monkeypatch, EMAIL)

    await auth_service.login_keycloak_user(claims(("vis-active",)), "kc-refresh-1")

    user = await sso_user(db_session)
    assert user.is_admin is True
    assert user.is_staff is True
    assert [role.name for role in user.roles] == ["vis-active"]


async def test_with_required_roles_set_admin_admits_a_token_without_roles(
    auth_service: AuthService,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(get_settings(), "KEYCLOAK_REQUIRE_ROLES", True)
    set_admin(monkeypatch, EMAIL)

    await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    assert (await sso_user(db_session)).is_admin is True


async def test_with_required_roles_other_users_still_need_roles(
    auth_service: AuthService,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(get_settings(), "KEYCLOAK_REQUIRE_ROLES", True)
    set_admin(monkeypatch, "someone.else@example.com")

    with pytest.raises(NotVisMember):
        await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")
