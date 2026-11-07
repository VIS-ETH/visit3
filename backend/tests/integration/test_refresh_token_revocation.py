import pytest

from app.core.exceptions import TokenInvalid
from app.models.user import User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


async def make_user(user_repository: UserRepository) -> User:
    return await user_repository.create_user(
        User(
            email="user@example.com",
            password="hash",
            is_company=True,
            email_confirmed=True,
        )
    )


async def test_a_refresh_racing_a_revocation_mints_no_live_session(
    user_repository: UserRepository,
    token_repository: TokenRepository,
    auth_service: AuthService,
    monkeypatch: pytest.MonkeyPatch,
):
    user = await make_user(user_repository)
    token = await token_repository.create_refresh_token(user.id)
    looked_up = TokenRepository.get_refresh_token_for_rotation

    async def revoke_after_lookup(self: TokenRepository, presented: str):
        found = await looked_up(self, presented)
        await self.revoke_all_refresh_tokens(user.id)
        return found

    monkeypatch.setattr(
        TokenRepository, "get_refresh_token_for_rotation", revoke_after_lookup
    )

    with pytest.raises(TokenInvalid):
        await auth_service.refresh_user(token)

    monkeypatch.setattr(TokenRepository, "get_refresh_token_for_rotation", looked_up)
    assert await token_repository.get_refresh_token_for_rotation(token) is None


async def test_a_logged_out_token_cannot_be_rotated_back_into_grace(
    user_repository: UserRepository, token_repository: TokenRepository
):
    user = await make_user(user_repository)
    token = await token_repository.create_refresh_token(user.id)
    await token_repository.revoke_refresh_token(user.id, token)

    assert await token_repository.rotate_refresh_token(token) is False
    assert await token_repository.get_refresh_token_for_rotation(token) is None
