import pytest

from app.core.exceptions import TokenInvalid
from app.models.user import User

NEW_PASSWORD = "new-long-password"


async def make_user(user_repository, email: str = "reset@example.com") -> User:
    return await user_repository.create_user(User(email=email, password="hash"))


async def request_reset_token(auth_service, mail_template_service, email: str) -> str:
    await auth_service.request_password_reset(email)
    context = mail_template_service.send.await_args.args[2]
    return context.reset_url.rsplit("/", 1)[1]


async def test_requesting_a_reset_invalidates_the_previous_token(
    auth_service,
    mail_template_service,
    user_repository,
):
    user = await make_user(user_repository)

    first = await request_reset_token(auth_service, mail_template_service, user.email)
    second = await request_reset_token(auth_service, mail_template_service, user.email)

    assert first != second
    assert await auth_service.validate_reset_token(first) is False
    assert await auth_service.validate_reset_token(second) is True


async def test_resetting_the_password_invalidates_the_other_reset_tokens(
    auth_service,
    token_repository,
    user_repository,
):
    user = await make_user(user_repository)
    first = await token_repository.create_reset_password_token(user.id)
    second = await token_repository.create_reset_password_token(user.id)

    assert await auth_service.reset_password(second, NEW_PASSWORD) is True

    with pytest.raises(TokenInvalid):
        await auth_service.reset_password(first, NEW_PASSWORD)
