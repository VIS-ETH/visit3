from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import col, update

from app.core.exceptions import TokenInvalid
from app.core.utils import hash_str
from app.models.user import RefreshToken
from app.repositories.token_repository import REFRESH_TOKEN_REUSE_GRACE


async def make_user(user_repository, email: str = "tabs@example.com"):
    return await user_repository.create_user(
        user_repository.model(email=email, password="hash")
    )


async def age_rotation(db_session, token: str, age: timedelta) -> None:
    await db_session.execute(
        update(RefreshToken)
        .where(col(RefreshToken.token) == hash_str(token))
        .values(rotated_at=datetime.now(timezone.utc) - age)
    )
    await db_session.commit()


async def test_second_tab_can_refresh_with_the_same_token(
    auth_service, user_repository, token_repository
):
    user = await make_user(user_repository)
    refresh_token = await token_repository.create_refresh_token(user.id)

    (_, first_rotated) = await auth_service.refresh_user(refresh_token)
    (_, second_rotated) = await auth_service.refresh_user(refresh_token)

    assert first_rotated != refresh_token
    assert second_rotated != refresh_token
    assert first_rotated != second_rotated
    assert await token_repository.get_active_refresh_token(first_rotated) is not None
    assert await token_repository.get_active_refresh_token(second_rotated) is not None


async def test_refresh_token_is_rejected_after_the_grace_window(
    auth_service, user_repository, token_repository, db_session
):
    user = await make_user(user_repository)
    refresh_token = await token_repository.create_refresh_token(user.id)

    await auth_service.refresh_user(refresh_token)
    await age_rotation(db_session, refresh_token, REFRESH_TOKEN_REUSE_GRACE * 2)

    with pytest.raises(TokenInvalid):
        await auth_service.refresh_user(refresh_token)


async def test_logged_out_refresh_token_is_rejected_immediately(
    auth_service, user_repository, token_repository
):
    user = await make_user(user_repository)
    refresh_token = await token_repository.create_refresh_token(user.id)

    await token_repository.revoke_refresh_token(user.id, refresh_token)

    with pytest.raises(TokenInvalid):
        await auth_service.refresh_user(refresh_token)


async def test_revoking_one_token_closes_its_rotation_grace(
    auth_service, user_repository, token_repository
):
    user = await make_user(user_repository)
    refresh_token = await token_repository.create_refresh_token(user.id)

    await auth_service.refresh_user(refresh_token)
    await token_repository.revoke_refresh_token(user.id, refresh_token)

    with pytest.raises(TokenInvalid):
        await auth_service.refresh_user(refresh_token)


async def test_revoking_all_tokens_closes_the_rotation_grace(
    auth_service, user_repository, token_repository
):
    user = await make_user(user_repository)
    refresh_token = await token_repository.create_refresh_token(user.id)

    await auth_service.refresh_user(refresh_token)
    await token_repository.revoke_all_refresh_tokens(user.id)

    with pytest.raises(TokenInvalid):
        await auth_service.refresh_user(refresh_token)


async def test_rotated_token_is_not_reusable_after_its_successor_rotates(
    auth_service, user_repository, token_repository, db_session
):
    user = await make_user(user_repository)
    refresh_token = await token_repository.create_refresh_token(user.id)

    (_, successor) = await auth_service.refresh_user(refresh_token)
    await auth_service.refresh_user(successor)
    await age_rotation(db_session, successor, REFRESH_TOKEN_REUSE_GRACE * 2)

    with pytest.raises(TokenInvalid):
        await auth_service.refresh_user(successor)
