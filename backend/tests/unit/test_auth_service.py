from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    EmailUsed,
    InvalidCredentials,
    NotAllowed,
    PasswordTooShort,
    TokenInvalid,
)
from app.core.utils import hash_str
from app.models.user import (
    ConfirmEmailToken,
    RefreshToken,
    ResetPasswordToken,
    Role,
    User,
)
from app.services.auth_service import AuthService


@dataclass
class AuthServiceHarness:
    service: AuthService
    user_repo: AsyncMock
    token_repo: AsyncMock
    role_repo: AsyncMock
    mail_service: AsyncMock


@pytest.fixture
def auth(
    user_repo,
    token_repo,
    role_repo,
    mail_service,
):
    return AuthServiceHarness(
        service=AuthService(user_repo, token_repo, role_repo, mail_service),
        user_repo=user_repo,
        token_repo=token_repo,
        role_repo=role_repo,
        mail_service=mail_service,
    )


async def test_register_user_rejects_duplicate_email(auth, make_user):
    existing_user = make_user(email="duplicate@example.com")
    auth.user_repo.get_by_email.return_value = existing_user

    with pytest.raises(EmailUsed):
        await auth.service.register_user(
            User(email="duplicate@example.com", password="long-enough")
        )

    auth.user_repo.create_user.assert_not_awaited()


@pytest.mark.parametrize("password", [None, "short"])
async def test_register_user_rejects_missing_or_short_password(
    auth,
    password,
):
    auth.user_repo.get_by_email.return_value = None

    with pytest.raises(PasswordTooShort):
        await auth.service.register_user(
            User(email="new@example.com", password=password)
        )

    auth.user_repo.create_user.assert_not_awaited()


async def test_register_user_normalizes_phone_and_saves_company_user(auth):
    auth.user_repo.get_by_email.return_value = None
    auth.user_repo.create_user.side_effect = lambda user: user
    auth.service.hash_password = AsyncMock(return_value="hashed-password")

    result = await auth.service.register_user(
        User(
            email="new@example.com",
            password="very-long-password",
            phone_number="079 123 45 67",
            is_admin=True,
            is_staff=True,
            is_company=False,
        )
    )

    auth.service.hash_password.assert_awaited_once_with("very-long-password")
    auth.user_repo.create_user.assert_awaited_once()
    created_user = auth.user_repo.create_user.await_args.args[0]
    assert result is created_user
    assert created_user.password == "hashed-password"
    assert created_user.phone_number == "+41791234567"
    assert created_user.is_admin is False
    assert created_user.is_staff is False
    assert created_user.is_company is True
    auth.token_repo.revoke_confirm_email_tokens.assert_awaited_once_with(
        created_user.id
    )
    auth.token_repo.create_confirm_email_token.assert_awaited_once()
    auth.mail_service.send_confirm_email_mail.assert_awaited_once()
    assert auth.mail_service.send_confirm_email_mail.await_args.args[0] == (
        created_user.email
    )


async def test_register_user_skips_confirmation_mail_for_confirmed_user(auth):
    confirmed_user = User(
        email="new@example.com",
        password="very-long-password",
        email_confirmed=True,
    )
    auth.user_repo.get_by_email.return_value = None
    auth.user_repo.create_user.return_value = confirmed_user
    auth.service.hash_password = AsyncMock(return_value="hashed-password")

    result = await auth.service.register_user(confirmed_user)

    assert result is confirmed_user
    auth.token_repo.revoke_confirm_email_tokens.assert_not_awaited()
    auth.token_repo.create_confirm_email_token.assert_not_awaited()
    auth.mail_service.send_confirm_email_mail.assert_not_awaited()


async def test_send_confirm_email_revokes_old_tokens_saves_new_token_and_sends_mail(
    auth,
    make_user,
):
    user = make_user(email="unconfirmed@example.com", email_confirmed=False)
    auth.token_repo.create_confirm_email_token.return_value = "confirm-token"

    await auth.service.send_confirm_email(user)

    auth.token_repo.revoke_confirm_email_tokens.assert_awaited_once_with(user.id)
    auth.token_repo.create_confirm_email_token.assert_awaited_once()
    assert auth.token_repo.create_confirm_email_token.await_args.args[0] == user.id
    auth.mail_service.send_confirm_email_mail.assert_awaited_once_with(
        user.email,
        "confirm-token",
    )


async def test_send_confirm_email_skips_confirmed_user(auth, make_user):
    user = make_user(email="confirmed@example.com", email_confirmed=True)

    await auth.service.send_confirm_email(user)

    auth.token_repo.revoke_confirm_email_tokens.assert_not_awaited()
    auth.token_repo.create_confirm_email_token.assert_not_awaited()
    auth.mail_service.send_confirm_email_mail.assert_not_awaited()


async def test_confirm_email_confirms_token_user_without_current_user(auth, make_user):
    user = make_user(email="confirm@example.com", email_confirmed=False)
    token = ConfirmEmailToken(
        user_id=user.id,
        token=hash_str("confirm-token"),
        expires_at=user.created_at,
    )
    auth.token_repo.get_confirm_email_token.return_value = token
    auth.user_repo.get_by_id.return_value = user

    result = await auth.service.confirm_email("confirm-token")

    assert result is True
    auth.token_repo.get_confirm_email_token.assert_awaited_once_with(
        "confirm-token"
    )
    auth.user_repo.get_by_id.assert_awaited_once_with(user.id)
    auth.user_repo.confirm_email.assert_awaited_once_with(user)
    auth.token_repo.revoke_confirm_email_tokens.assert_awaited_once_with(user.id)


async def test_confirm_email_raises_for_invalid_public_token(auth):
    auth.token_repo.get_confirm_email_token.return_value = None

    with pytest.raises(TokenInvalid):
        await auth.service.confirm_email("bad-token")

    auth.user_repo.confirm_email.assert_not_awaited()


async def test_validate_confirm_email_token_uses_public_token_lookup(auth):
    auth.token_repo.get_confirm_email_token.return_value = object()

    result = await auth.service.validate_confirm_email_token("confirm-token")

    assert result is True
    auth.token_repo.get_confirm_email_token.assert_awaited_once_with(
        "confirm-token"
    )


async def test_login_user_rejects_invalid_credentials(auth):
    auth.service.authenticate_user = AsyncMock(return_value=False)

    with pytest.raises(InvalidCredentials):
        await auth.service.login_user("user@example.com", "wrong-password")

    auth.service.authenticate_user.assert_awaited_once_with(
        "user@example.com",
        "wrong-password",
    )


async def test_login_user_returns_created_tokens(auth, make_user):
    user = make_user(email="user@example.com")
    auth.service.authenticate_user = AsyncMock(return_value=user)
    auth.service.create_tokens = AsyncMock(
        return_value=("access-token", "refresh-token")
    )

    result = await auth.service.login_user("user@example.com", "password")

    assert result == ("access-token", "refresh-token")
    auth.service.create_tokens.assert_awaited_once_with(user)


async def test_refresh_user_rotates_refresh_token(auth, make_user):
    user = make_user()
    token = RefreshToken(
        user_id=user.id,
        token=hash_str("old-refresh-token"),
        expires_at=user.created_at,
    )
    auth.service.get_active_refresh_token = AsyncMock(return_value=token)
    auth.service.create_tokens = AsyncMock(return_value=("new-access", "new-refresh"))
    auth.user_repo.get_by_id.return_value = user

    result = await auth.service.refresh_user("old-refresh-token")

    assert result == ("new-access", "new-refresh")
    auth.token_repo.revoke_refresh_token.assert_awaited_once_with(
        user.id, "old-refresh-token"
    )


@pytest.mark.parametrize("refresh_token", ["", None])
async def test_refresh_user_rejects_missing_token(auth, refresh_token):
    with pytest.raises(TokenInvalid):
        await auth.service.refresh_user(refresh_token)

    auth.user_repo.get_by_id.assert_not_awaited()


async def test_reset_password_rejects_invalid_token(auth):
    auth.token_repo.get_reset_password_token.return_value = None

    with pytest.raises(TokenInvalid):
        await auth.service.reset_password("bad-token", "new-long-password")

    auth.user_repo.update_password.assert_not_awaited()


async def test_reset_password_updates_password_and_revokes_tokens(auth, make_user):
    user = make_user()
    reset_token = ResetPasswordToken(
        user_id=user.id,
        token=hash_str("reset-token"),
        expires_at=user.created_at,
    )
    auth.token_repo.get_reset_password_token.return_value = reset_token
    auth.service.hash_password = AsyncMock(return_value="new-hash")

    result = await auth.service.reset_password("reset-token", "new-long-password")

    assert result is True
    auth.user_repo.update_password.assert_awaited_once_with(user.id, "new-hash")
    auth.token_repo.revoke_all_refresh_tokens.assert_awaited_once_with(user.id)
    auth.token_repo.revoke_reset_password_token.assert_awaited_once_with(
        "reset-token"
    )


async def test_map_keycloak_roles_filters_roles_and_marks_admin(auth):
    active_role = Role(name="vis-active")
    admin_role = Role(name="admin")
    auth.role_repo.get_or_create.side_effect = [active_role, admin_role]

    is_admin, roles = await auth.service.map_keycloak_roles(
        ["ignored", "vis-active", "admin"],
        ["vis-active", "admin"],
    )

    assert is_admin is True
    assert roles == [active_role, admin_role]


async def test_request_password_reset_returns_silently_for_unknown_email(auth):
    auth.user_repo.get_by_email.return_value = None

    await auth.service.request_password_reset("missing@example.com")

    auth.token_repo.create_reset_password_token.assert_not_awaited()
    auth.mail_service.send_reset_password_mail.assert_not_awaited()


async def test_request_password_reset_rejects_oauth_only_user(
    auth,
    make_user,
):
    auth.user_repo.get_by_email.return_value = make_user(
        email="oauth@example.com",
        password=None,
    )

    with pytest.raises(NotAllowed):
        await auth.service.request_password_reset("oauth@example.com")

    auth.mail_service.send_reset_password_mail.assert_not_awaited()


async def test_request_password_reset_sends_reset_mail_for_password_user(
    auth,
    make_user,
):
    password_user = make_user(email="user@example.com")
    auth.user_repo.get_by_email.return_value = password_user
    auth.service.create_reset_password_token = AsyncMock(return_value="reset-token")

    await auth.service.request_password_reset("user@example.com")

    auth.service.create_reset_password_token.assert_awaited_once_with(password_user)
    auth.mail_service.send_reset_password_mail.assert_awaited_once_with(
        "user@example.com",
        "reset-token",
    )
