from datetime import datetime, timedelta, timezone

from sqlmodel import col, update

from app.core.utils import hash_str
from app.models.user import RefreshToken
from app.repositories.token_repository import REFRESH_TOKEN_REUSE_GRACE


async def age_rotation(db_session, token: str, age: timedelta) -> None:
    await db_session.execute(
        update(RefreshToken)
        .where(col(RefreshToken.token) == hash_str(token))
        .values(rotated_at=datetime.now(timezone.utc) - age)
    )
    await db_session.commit()


async def make_user(user_repository, email: str = "rotation@example.com"):
    return await user_repository.create_user(
        user_repository.model(email=email, password="hash")
    )


async def test_rotated_token_stays_usable_inside_the_grace_window(
    user_repository, token_repository
):
    user = await make_user(user_repository)
    token = await token_repository.create_refresh_token(user.id)

    await token_repository.rotate_refresh_token(user.id, token)

    assert await token_repository.get_active_refresh_token(token) is None
    assert await token_repository.get_refresh_token_for_rotation(token) is not None


async def test_rotated_token_expires_from_the_grace_window(
    user_repository, token_repository, db_session
):
    user = await make_user(user_repository)
    token = await token_repository.create_refresh_token(user.id)

    await token_repository.rotate_refresh_token(user.id, token)
    await age_rotation(db_session, token, REFRESH_TOKEN_REUSE_GRACE * 2)

    assert await token_repository.get_refresh_token_for_rotation(token) is None


async def test_revoked_token_gets_no_grace_window(user_repository, token_repository):
    user = await make_user(user_repository)
    token = await token_repository.create_refresh_token(user.id)

    await token_repository.revoke_refresh_token(user.id, token)

    assert await token_repository.get_refresh_token_for_rotation(token) is None


async def test_expired_token_gets_no_grace_window(
    user_repository, token_repository, db_session
):
    user = await make_user(user_repository)
    token = await token_repository.create_refresh_token(user.id)

    await token_repository.rotate_refresh_token(user.id, token)
    await db_session.execute(
        update(RefreshToken)
        .where(col(RefreshToken.token) == hash_str(token))
        .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    )
    await db_session.commit()

    assert await token_repository.get_refresh_token_for_rotation(token) is None


async def test_rotation_only_affects_the_presented_token(
    monkeypatch, user_repository, token_repository
):
    user = await make_user(user_repository)
    token_values = iter(["first-token", "second-token"])
    monkeypatch.setattr(
        token_repository, "_create_token_value", lambda length: next(token_values)
    )
    first = await token_repository.create_refresh_token(user.id)
    second = await token_repository.create_refresh_token(user.id)

    await token_repository.rotate_refresh_token(user.id, first)

    assert await token_repository.get_active_refresh_token(second) is not None
