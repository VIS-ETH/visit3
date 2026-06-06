from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.models.user import ConfirmEmailToken, ForgetPasswordToken, RefreshToken


async def test_confirm_email_token_validation_respects_revocation(
    user_repository,
    token_repository,
):
    user = await user_repository.create_user(
        user_repository.model(email="user@example.com", password="hash")
    )
    await token_repository.save_confirm_email_token(
        "hashed-token",
        user.id,
        datetime.now(timezone.utc) + timedelta(days=1),
    )

    assert await token_repository.validate_confirm_email_token(
        user.id,
        "hashed-token",
    )

    await token_repository.revoke_confirm_email_tokens(user.id)

    assert not await token_repository.validate_confirm_email_token(
        user.id,
        "hashed-token",
    )


async def test_confirm_email_token_public_lookup_respects_active_state(
    user_repository,
    token_repository,
):
    user = await user_repository.create_user(
        user_repository.model(email="public-token@example.com", password="hash")
    )
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    await token_repository.save_confirm_email_token(
        "active-public-token",
        user.id,
        expires_at,
    )

    token = await token_repository.get_confirm_email_token("active-public-token")

    assert token is not None
    assert token.user_id == user.id

    await token_repository.revoke_confirm_email_tokens(user.id)

    assert await token_repository.get_confirm_email_token("active-public-token") is None


async def test_confirm_email_token_public_lookup_rejects_expired_token(
    user_repository,
    token_repository,
):
    user = await user_repository.create_user(
        user_repository.model(email="expired-public-token@example.com", password="hash")
    )
    await token_repository.save_confirm_email_token(
        "expired-public-token",
        user.id,
        datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert await token_repository.get_confirm_email_token("expired-public-token") is None


async def test_expired_forget_password_token_is_not_active(
    user_repository,
    token_repository,
):
    user = await user_repository.create_user(
        user_repository.model(email="user@example.com", password="hash")
    )
    await token_repository.save_forget_password_token(
        "expired-token",
        user.id,
        datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert await token_repository.get_forget_password_token("expired-token") is None


async def test_revoke_refresh_token_only_revokes_matching_token(
    user_repository,
    token_repository,
):
    user = await user_repository.create_user(
        user_repository.model(email="user@example.com", password="hash")
    )
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    await token_repository.create_refresh_token(user.id, "token-one", expires_at)
    await token_repository.create_refresh_token(user.id, "token-two", expires_at)

    await token_repository.revoke_refresh_token(user.id, "token-one")

    assert await token_repository.get_active_refresh_token("token-one") is None
    assert await token_repository.get_active_refresh_token("token-two") is not None


async def test_cleanup_expired_removes_expired_and_revoked_tokens(
    user_repository,
    token_repository,
    db_session,
):
    user = await user_repository.create_user(
        user_repository.model(email="cleanup@example.com", password="hash")
    )
    now = datetime.now(timezone.utc)
    await token_repository.create_refresh_token(
        user.id,
        "active-refresh",
        now + timedelta(days=1),
    )
    await token_repository.create_refresh_token(
        user.id,
        "expired-refresh",
        now - timedelta(seconds=1),
    )
    await token_repository.save_forget_password_token(
        "revoked-forget",
        user.id,
        now + timedelta(days=1),
    )
    await token_repository.save_confirm_email_token(
        "expired-confirm",
        user.id,
        now - timedelta(seconds=1),
    )
    await token_repository.revoke_forget_password_token("revoked-forget")

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
    forget_tokens = (
        (await db_session.execute(select(ForgetPasswordToken.token))).scalars().all()
    )
    confirm_tokens = (
        (await db_session.execute(select(ConfirmEmailToken.token))).scalars().all()
    )
    assert refresh_tokens == ["active-refresh"]
    assert forget_tokens == []
    assert confirm_tokens == []
