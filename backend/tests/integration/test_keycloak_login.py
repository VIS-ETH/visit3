import warnings
from collections.abc import Sequence
from typing import Any

import jwt
import pytest
from sqlalchemy.exc import SAWarning

from app.core.config import get_settings
from app.core.exceptions import EmailTakenLocally, EmailUsed, NotVisMember
from app.models.user import User
from app.services.auth_service import UNKNOWN_NAME

LOCAL_PASSWORD_HASH = "local-password-hash"


def keycloak_token(
    *,
    sub: str,
    email: str,
    roles: Sequence[str] = ("vis-active",),
    first_name: str | None = "Ada",
    last_name: str | None = "Lovelace",
    name: str | None = None,
    preferred_username: str | None = None,
) -> dict[str, Any]:
    token: dict[str, Any] = {
        "sub": sub,
        "email": email,
        "resource_access": {
            get_settings().SIP_AUTH_OIDC_CLIENT_ID: {"roles": list(roles)}
        },
    }
    optional_claims = {
        "given_name": first_name,
        "family_name": last_name,
        "name": name,
        "preferred_username": preferred_username,
    }
    token.update(
        {key: value for key, value in optional_claims.items() if value is not None}
    )
    return token


async def make_local_user(user_repository, company_repository, email: str) -> User:
    company = await company_repository.create_company("Acme AG")
    return await user_repository.create_user(
        User(
            email=email,
            password=LOCAL_PASSWORD_HASH,
            is_company=True,
            company_id=company.id,
            user_confirmed=True,
            email_confirmed=True,
        )
    )


async def test_keycloak_login_refuses_email_of_local_account(
    auth_service,
    user_repository,
    company_repository,
):
    local_user = await make_local_user(
        user_repository, company_repository, "ada@example.com"
    )

    with pytest.raises(EmailTakenLocally) as error:
        await auth_service.map_keycloak_to_user(
            keycloak_token(sub="keycloak-sub", email=local_user.email)
        )

    assert error.value.code == "auth.email_taken_locally"
    assert error.value.status_code == 403


async def test_keycloak_login_leaves_local_account_untouched(
    auth_service,
    user_repository,
    company_repository,
    db_session,
):
    local_user = await make_local_user(
        user_repository, company_repository, "ada@example.com"
    )

    with pytest.raises(EmailTakenLocally):
        await auth_service.map_keycloak_to_user(
            keycloak_token(sub="keycloak-sub", email=local_user.email)
        )

    db_session.expire_all()
    stored = await user_repository.get_by_email("ada@example.com")
    assert stored is not None
    assert stored.password == LOCAL_PASSWORD_HASH
    assert stored.company_id == local_user.company_id
    assert stored.is_company is True
    assert stored.is_staff is False
    assert stored.sub is None


async def test_keycloak_login_refuses_email_of_another_keycloak_account(
    auth_service,
    user_repository,
):
    await auth_service.map_keycloak_to_user(
        keycloak_token(sub="first-sub", email="shared@example.com")
    )

    with pytest.raises(EmailUsed):
        await auth_service.map_keycloak_to_user(
            keycloak_token(sub="second-sub", email="shared@example.com")
        )

    assert len(await user_repository.get_users()) == 1


async def test_keycloak_first_login_creates_staff_user(
    auth_service,
    user_repository,
):
    user = await auth_service.map_keycloak_to_user(
        keycloak_token(sub="new-sub", email="new@example.com")
    )

    assert user.sub == "new-sub"
    assert user.password is None
    assert user.is_staff is True
    assert user.is_company is False
    assert user.company_id is None
    assert user.user_confirmed is True
    assert user.email_confirmed is True
    loaded = await user_repository.load_user_roles(user)
    assert [role.name for role in loaded.roles] == ["vis-active"]


async def test_keycloak_login_attaches_roles_inside_the_session(auth_service):
    with warnings.catch_warnings():
        warnings.simplefilter("error", SAWarning)
        first = await auth_service.map_keycloak_to_user(
            keycloak_token(sub="clean-sub", email="clean@example.com")
        )
        again = await auth_service.map_keycloak_to_user(
            keycloak_token(sub="clean-sub", email="clean@example.com")
        )

    assert first.id == again.id


async def test_keycloak_login_marks_vis_member_as_staff(auth_service):
    user = await auth_service.map_keycloak_to_user(
        keycloak_token(sub="member-sub", email="member@example.com")
    )

    assert user.is_staff is True
    assert user.is_admin is False


async def test_keycloak_login_marks_admin_role_as_staff_and_admin(
    auth_service,
    user_repository,
):
    user = await auth_service.map_keycloak_to_user(
        keycloak_token(
            sub="admin-sub",
            email="admin@example.com",
            roles=("vis-active", "admin"),
        )
    )

    assert user.is_staff is True
    assert user.is_admin is True
    loaded = await user_repository.load_user_roles(user)
    assert {role.name for role in loaded.roles} == {"vis-active", "admin"}


async def test_keycloak_login_rejects_user_without_vis_role(
    auth_service,
    user_repository,
):
    with pytest.raises(NotVisMember) as error:
        await auth_service.map_keycloak_to_user(
            keycloak_token(
                sub="outsider-sub",
                email="outsider@example.com",
                roles=("some-other-app-role",),
            )
        )

    assert error.value.code == "auth.not_vis_member"
    assert error.value.status_code == 403
    assert await user_repository.get_by_email("outsider@example.com") is None


async def test_keycloak_login_downgrades_flags_when_admin_role_is_removed(
    auth_service,
    user_repository,
):
    first = await auth_service.map_keycloak_to_user(
        keycloak_token(
            sub="downgrade-sub",
            email="downgrade@example.com",
            roles=("vis-active", "admin"),
        )
    )

    second = await auth_service.map_keycloak_to_user(
        keycloak_token(
            sub="downgrade-sub",
            email="downgrade@example.com",
            roles=("vis-active",),
        )
    )

    assert second.id == first.id
    assert second.is_admin is False
    assert second.is_staff is True
    loaded = await user_repository.load_user_roles(second)
    assert [role.name for role in loaded.roles] == ["vis-active"]


async def test_keycloak_repeat_login_updates_names_of_the_sub_row(
    auth_service,
    user_repository,
):
    first = await auth_service.map_keycloak_to_user(
        keycloak_token(sub="same-sub", email="ada@example.com")
    )

    second = await auth_service.map_keycloak_to_user(
        keycloak_token(
            sub="same-sub",
            email="ada.byron@example.com",
            first_name="Augusta",
            last_name="Byron",
        )
    )

    assert second.id == first.id
    assert second.first_name == "Augusta"
    assert second.last_name == "Byron"
    assert second.email == "ada.byron@example.com"
    assert len(await user_repository.get_users()) == 1


async def test_keycloak_login_without_names_uses_full_name_claim(auth_service):
    user = await auth_service.map_keycloak_to_user(
        keycloak_token(
            sub="name-claim-sub",
            email="ada@example.com",
            first_name=None,
            last_name=None,
            name="Augusta Ada Byron",
        )
    )

    assert user.first_name == "Augusta"
    assert user.last_name == "Ada Byron"


async def test_keycloak_login_without_names_uses_preferred_username(auth_service):
    user = await auth_service.map_keycloak_to_user(
        keycloak_token(
            sub="username-sub",
            email="ada@example.com",
            first_name=None,
            last_name=None,
            preferred_username="alovelace",
        )
    )

    assert user.first_name == "alovelace"
    assert user.last_name == UNKNOWN_NAME


async def test_keycloak_login_without_any_name_claim_uses_email_local_part(
    auth_service,
):
    user = await auth_service.map_keycloak_to_user(
        keycloak_token(
            sub="bare-sub",
            email="ada@example.com",
            first_name=None,
            last_name=None,
        )
    )

    assert user.first_name == "ada"
    assert user.last_name == UNKNOWN_NAME


async def test_keycloak_login_keeps_given_name_when_family_name_is_missing(
    auth_service,
):
    user = await auth_service.map_keycloak_to_user(
        keycloak_token(
            sub="partial-sub",
            email="ada@example.com",
            last_name=None,
            preferred_username="lovelace",
        )
    )

    assert user.first_name == "Ada"
    assert user.last_name == UNKNOWN_NAME


def access_token_subject(token: str) -> str:
    payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
    return payload["sub"]


async def test_access_token_of_keycloak_user_carries_the_internal_user_id(
    auth_service,
):
    user = await auth_service.map_keycloak_to_user(
        keycloak_token(sub="keycloak-sub", email="ada@example.com")
    )

    token = await auth_service.create_access_token(user)

    assert access_token_subject(token) == str(user.id)
    assert access_token_subject(token) != user.sub


async def test_access_token_of_local_user_carries_the_internal_user_id(
    auth_service,
    user_repository,
    company_repository,
):
    local_user = await make_local_user(
        user_repository, company_repository, "local@example.com"
    )

    token = await auth_service.create_access_token(local_user)

    assert access_token_subject(token) == str(local_user.id)
