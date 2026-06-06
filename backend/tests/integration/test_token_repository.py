from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.core.utils import hash_str
from app.models.user import ConfirmEmailToken, RefreshToken, ResetPasswordToken


def use_token_values(monkeypatch, token_repository, *tokens: str) -> None:
    token_values = iter(tokens)
    monkeypatch.setattr(
        token_repository,
        "_create_token_value",
        lambda length: next(token_values),
    )


async def test_confirm_email_token_public_lookup_respects_active_state(
    monkeypatch,
    user_repository,
    token_repository,
):
    user = await user_repository.create_user(
        user_repository.model(email="public-token@example.com", password="hash")
    )
    use_token_values(monkeypatch, token_repository, "active-public-token")
    token_value = await token_repository.create_confirm_email_token(user.id)

    token = await token_repository.get_confirm_email_token(token_value)

    assert token is not None
    assert token.user_id == user.id
    assert token.token == hash_str(token_value)

    await token_repository.revoke_confirm_email_tokens(user.id)

    assert await token_repository.get_confirm_email_token(token_value) is None


async def test_confirm_email_token_public_lookup_rejects_expired_token(
    user_repository,
    token_repository,
):
    user = await user_repository.create_user(
        user_repository.model(email="expired-public-token@example.com", password="hash")
    )
    token = "expired-public-token"
    await token_repository._create_token(
        ConfirmEmailToken,
        user_id=user.id,
        hashed_token=hash_str(token),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert await token_repository.get_confirm_email_token(token) is None


async def test_expired_reset_password_token_is_not_active(
    user_repository,
    token_repository,
):
    user = await user_repository.create_user(
        user_repository.model(email="user@example.com", password="hash")
    )
    token = "expired-token"
    await token_repository._create_token(
        ResetPasswordToken,
        user_id=user.id,
        hashed_token=hash_str(token),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert await token_repository.get_reset_password_token(token) is None


async def test_revoke_refresh_token_only_revokes_matching_token(
    monkeypatch,
    user_repository,
    token_repository,
):
    user = await user_repository.create_user(
        user_repository.model(email="user@example.com", password="hash")
    )
    use_token_values(monkeypatch, token_repository, "token-one", "token-two")
    token_one = await token_repository.create_refresh_token(user.id)
    token_two = await token_repository.create_refresh_token(user.id)

    await token_repository.revoke_refresh_token(user.id, token_one)

    assert await token_repository.get_active_refresh_token(token_one) is None
    assert await token_repository.get_active_refresh_token(token_two) is not None


async def test_cleanup_expired_removes_expired_and_revoked_tokens(
    monkeypatch,
    user_repository,
    token_repository,
    db_session,
):
    user = await user_repository.create_user(
        user_repository.model(email="cleanup@example.com", password="hash")
    )
    now = datetime.now(timezone.utc)
    use_token_values(
        monkeypatch,
        token_repository,
        "active-refresh",
        "expired-refresh",
        "revoked-forget",
        "expired-confirm",
    )
    await token_repository.create_refresh_token(user.id)
    await token_repository._create_token(
        RefreshToken,
        user_id=user.id,
        hashed_token=hash_str("expired-refresh"),
        expires_at=now - timedelta(seconds=1),
    )
    revoked_reset = await token_repository.create_reset_password_token(user.id)
    await token_repository._create_token(
        ConfirmEmailToken,
        user_id=user.id,
        hashed_token=hash_str("expired-confirm"),
        expires_at=now - timedelta(seconds=1),
    )
    await token_repository.revoke_reset_password_token(revoked_reset)

    await token_repository.cleanup_expired()

    refresh_tokens = (
        (
            await db_session.execute(
                select(RefreshToken.token).order_by(RefreshToken.token)
            )
        )
        .scalars()
        .all()
    )
    reset_tokens = (
        (await db_session.execute(select(ResetPasswordToken.token))).scalars().all()
    )
    confirm_tokens = (
        (await db_session.execute(select(ConfirmEmailToken.token))).scalars().all()
    )
    assert refresh_tokens == [hash_str("active-refresh")]
    assert reset_tokens == []
    assert confirm_tokens == []
