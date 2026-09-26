from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.config import get_settings
from app.core.exceptions import EmailTakenLocally, NotVisMember
from app.models.user import User
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


async def test_an_unknown_subject_is_rejected_and_nothing_is_created(
    auth_service: AuthService, db_session: AsyncSession
):
    with pytest.raises(NotVisMember):
        await auth_service.login_keycloak_user(
            claims(("vis-active", "admin")), "kc-refresh-1"
        )

    assert await UserRepository(db_session).get_by_sub(SUB) is None
    assert await UserRepository(db_session).get_by_email(EMAIL) is None


async def test_an_existing_non_staff_account_is_rejected_and_kept(
    auth_service: AuthService, db_session: AsyncSession
):
    await stored_user(db_session, is_staff=False, is_admin=False, is_company=True)

    with pytest.raises(NotVisMember):
        await auth_service.login_keycloak_user(claims(("vis-active",)), "kc-refresh-1")

    user = await sso_user(db_session)
    assert user.is_staff is False
    assert user.is_company is True


async def test_an_unconfirmed_local_account_is_not_replaced(
    auth_service: AuthService,
    create_user: Callable[..., Awaitable[User]],
    db_session: AsyncSession,
):
    local = await create_user(email=EMAIL, email_confirmed=False, user_confirmed=False)

    with pytest.raises(NotVisMember):
        await auth_service.login_keycloak_user(claims(), "kc-refresh-1")

    kept = await UserRepository(db_session).get_by_email(EMAIL)
    assert kept is not None
    assert kept.id == local.id


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


async def test_a_refresh_ends_once_the_account_is_no_longer_staff(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
):
    user = await stored_user(
        db_session, is_staff=True, is_admin=False, is_company=False
    )
    refresh_token = await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")
    user.is_staff = False
    db_session.add(user)
    await db_session.commit()

    response = await refresh(client, csrf_headers, refresh_token)

    assert response.status_code == 401
    remaining = await db_session.execute(select(User).where(col(User.id) == user.id))
    assert remaining.scalar_one().is_staff is False


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


async def test_set_admin_does_not_admit_other_emails(
    auth_service: AuthService,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    set_admin(monkeypatch, "someone.else@example.com")

    with pytest.raises(NotVisMember):
        await auth_service.login_keycloak_user(claims(()), "kc-refresh-1")

    assert await UserRepository(db_session).get_by_sub(SUB) is None


async def test_set_admin_requires_a_verified_email_when_the_claim_is_present(
    auth_service: AuthService,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    set_admin(monkeypatch, EMAIL)

    with pytest.raises(NotVisMember):
        await auth_service.login_keycloak_user(
            {**claims(()), "email_verified": False}, "kc-refresh-1"
        )

    assert await UserRepository(db_session).get_by_sub(SUB) is None


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
