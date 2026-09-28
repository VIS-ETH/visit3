from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select, update

from app.core.config import get_settings
from app.core.exceptions import KeycloakExchangeFailed, NotVisMember
from app.core.utils import hash_str
from app.models.user import RefreshToken, User
from app.repositories.token_repository import REFRESH_TOKEN_REUSE_GRACE
from app.repositories.user_repository import UserRepository
from app.services import auth_service as auth_module
from app.services.auth_service import AuthService
from tests.api.conftest import DEFAULT_PASSWORD

SUB = "keycloak-subject-1"
EMAIL = "board.member@example.com"


def claims(roles: Sequence[str] = ("vis-active",)) -> dict[str, Any]:
    return {
        "sub": SUB,
        "email": EMAIL,
        "given_name": "Grace",
        "family_name": "Hopper",
        "resource_access": {
            get_settings().SIP_AUTH_OIDC_CLIENT_ID: {"roles": list(roles)}
        },
    }


class FakeKeycloak:
    def __init__(self) -> None:
        self.roles: Sequence[str] = ("vis-active",)
        self.status = 200
        self.unreachable = False
        self.requests: list[dict[str, str]] = []
        self.issued = 0

    async def token_endpoint(self, data: dict[str, str]) -> Response:
        if self.unreachable:
            raise KeycloakExchangeFailed("keycloak:unreachable:ConnectError")
        self.requests.append(data)
        self.issued += 1
        body = {
            "access_token": f"kc-access-{self.issued}",
            "refresh_token": f"kc-refresh-{self.issued + 1}",
        }
        return Response(self.status, json=body)

    def decode(self, token: str | None) -> dict[str, Any] | None:
        return claims(self.roles) if token else None


@pytest.fixture
def keycloak(monkeypatch: pytest.MonkeyPatch) -> FakeKeycloak:
    fake = FakeKeycloak()
    monkeypatch.setattr(AuthService, "_token_endpoint", fake.token_endpoint)
    monkeypatch.setattr(auth_module, "decode_token", fake.decode)
    return fake


async def sso_login(auth_service: AuthService) -> str:
    return await auth_service.login_keycloak_user(claims(), "kc-refresh-1")


async def refresh(
    client: AsyncClient, csrf_headers: dict[str, str], refresh_token: str
) -> Response:
    client.cookies.set("refresh_token", refresh_token)
    return await client.post("/api/auth/refresh", headers=csrf_headers)


async def sso_user(db_session: AsyncSession) -> User:
    user = await UserRepository(db_session).get_by_sub(SUB)
    assert user is not None
    await db_session.refresh(user)
    return user


async def active_tokens(db_session: AsyncSession, user: User) -> int:
    result = await db_session.execute(
        select(RefreshToken).where(
            col(RefreshToken.user_id) == user.id,
            col(RefreshToken.is_revoked) == False,
        )
    )
    return len(result.scalars().all())


async def test_a_refresh_revalidates_the_sso_session_with_keycloak(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
):
    first = await refresh(client, csrf_headers, await sso_login(auth_service))
    second = await refresh(client, csrf_headers, first.cookies["refresh_token"])

    assert first.status_code == second.status_code == 200
    assert [request["grant_type"] for request in keycloak.requests] == [
        "refresh_token",
        "refresh_token",
    ]
    assert [request["refresh_token"] for request in keycloak.requests] == [
        "kc-refresh-1",
        "kc-refresh-2",
    ]
    assert keycloak.requests[0]["client_id"] == get_settings().SIP_AUTH_OIDC_CLIENT_ID


async def test_a_refresh_ends_the_session_when_keycloak_ended_it(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
):
    refresh_token = await sso_login(auth_service)
    keycloak.status = 400

    response = await refresh(client, csrf_headers, refresh_token)

    assert response.status_code == 401
    assert await active_tokens(db_session, await sso_user(db_session)) == 0


async def test_a_refresh_offboards_a_user_who_lost_the_vis_roles(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
):
    refresh_token = await sso_login(auth_service)
    other_device = await sso_login(auth_service)
    keycloak.roles = ()

    response = await refresh(client, csrf_headers, refresh_token)
    other = await refresh(client, csrf_headers, other_device)

    user = await sso_user(db_session)
    assert response.status_code == other.status_code == 401
    assert user.is_staff is False
    assert user.is_admin is False
    assert await active_tokens(db_session, user) == 0


async def test_a_refresh_drops_admin_rights_removed_in_keycloak(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
    db_session: AsyncSession,
):
    await auth_service.login_keycloak_user(
        claims(("vis-active", get_settings().ADMIN_GROUP)), "kc-refresh-1"
    )
    refresh_token = await sso_login(auth_service)
    keycloak.roles = ("vis-active",)

    response = await refresh(client, csrf_headers, refresh_token)

    user = await sso_user(db_session)
    assert response.status_code == 200
    assert user.is_staff is True
    assert user.is_admin is False


async def test_a_refresh_keeps_the_session_while_keycloak_is_unreachable(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
):
    refresh_token = await sso_login(auth_service)
    keycloak.unreachable = True

    outage = await refresh(client, csrf_headers, refresh_token)
    keycloak.unreachable = False
    recovered = await refresh(client, csrf_headers, refresh_token)

    assert outage.status_code == 503
    assert outage.json()["code"] == "error.identity_provider_unavailable"
    assert recovered.status_code == 200


async def test_an_sso_session_without_a_keycloak_token_must_log_in_again(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    auth_service: AuthService,
    keycloak: FakeKeycloak,
):
    legacy = await auth_service.login_keycloak_user(claims())

    response = await refresh(client, csrf_headers, legacy)

    assert response.status_code == 401
    assert keycloak.requests == []


async def test_a_lost_vis_role_at_login_clears_flags_and_sessions(
    auth_service: AuthService,
    db_session: AsyncSession,
):
    await sso_login(auth_service)

    with pytest.raises(NotVisMember):
        await auth_service.login_keycloak_user(claims(()), "kc-refresh-9")

    user = await sso_user(db_session)
    assert user.is_staff is False
    assert user.is_admin is False
    assert await active_tokens(db_session, user) == 0


async def test_token_reuse_only_ends_the_affected_session(
    client: AsyncClient,
    csrf_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    db_session: AsyncSession,
):
    user = await create_user(email="two.devices@example.com")

    async def login() -> str:
        response = await client.post(
            "/api/auth/login",
            data={"username": user.email, "password": DEFAULT_PASSWORD},
            headers=csrf_headers,
        )
        return response.cookies["refresh_token"]

    laptop = await login()
    phone = await login()
    stolen = laptop
    laptop = (await refresh(client, csrf_headers, laptop)).cookies["refresh_token"]
    await db_session.execute(
        update(RefreshToken)
        .where(col(RefreshToken.token) == hash_str(stolen))
        .values(rotated_at=datetime.now(timezone.utc) - REFRESH_TOKEN_REUSE_GRACE * 2)
    )
    await db_session.commit()

    reuse = await refresh(client, csrf_headers, stolen)
    laptop_after = await refresh(client, csrf_headers, laptop)
    phone_after = await refresh(client, csrf_headers, phone)

    assert reuse.status_code == 401
    assert laptop_after.status_code == 401
    assert phone_after.status_code == 200


async def test_expired_rotation_records_survive_cleanup_until_they_expire(
    create_user: Callable[..., Awaitable[User]],
    db_session: AsyncSession,
    auth_service: AuthService,
):
    user = await create_user(email="cleanup@example.com")
    token = await auth_service.create_refresh_token(user)
    await auth_service.token_repository.rotate_refresh_token(user.id, token)
    await db_session.execute(
        update(RefreshToken)
        .where(col(RefreshToken.token) == hash_str(token))
        .values(rotated_at=datetime.now(timezone.utc) - timedelta(hours=2))
    )
    await db_session.commit()

    await auth_service.token_repository.cleanup_expired()

    remaining = await db_session.execute(
        select(RefreshToken).where(col(RefreshToken.token) == hash_str(token))
    )
    assert remaining.scalar_one_or_none() is not None
