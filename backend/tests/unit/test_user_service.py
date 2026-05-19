from dataclasses import dataclass
from datetime import datetime
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    NotAllowed,
    PhoneNumberInvalid,
    TokenInvalid,
    UserNotFound,
)
from app.core.utils import hash_str
from app.services.user_service import UserService


@dataclass
class UserServiceHarness:
    service: UserService
    user_repo: AsyncMock
    token_repo: AsyncMock
    mail_service: AsyncMock


@pytest.fixture
def user_service(user_repo, token_repo, mail_service, unconfirmed_user):
    return UserServiceHarness(
        service=UserService(user_repo, token_repo, mail_service, unconfirmed_user),
        user_repo=user_repo,
        token_repo=token_repo,
        mail_service=mail_service,
    )


async def test_send_confirmation_mail_revokes_old_tokens_saves_new_token_and_sends_mail(
    monkeypatch,
    user_service,
    unconfirmed_user,
):
    monkeypatch.setattr(
        "app.services.user_service.secrets.token_urlsafe",
        lambda length: "raw-confirm-token",
    )

    await user_service.service.send_confirmation_mail()

    user_service.token_repo.revoke_confirm_email_tokens.assert_awaited_once_with(
        unconfirmed_user.id
    )
    user_service.token_repo.save_confirm_email_token.assert_awaited_once_with(
        hash_str("raw-confirm-token"),
        unconfirmed_user.id,
        ANY,
    )
    expires_at = user_service.token_repo.save_confirm_email_token.await_args.args[2]
    assert isinstance(expires_at, datetime)
    user_service.mail_service.send_confirm_email_mail.assert_awaited_once_with(
        unconfirmed_user.email,
        "raw-confirm-token",
    )


async def test_send_confirmation_mail_skips_confirmed_user(
    user_repo,
    token_repo,
    mail_service,
    company_user,
):
    service = UserService(user_repo, token_repo, mail_service, company_user)

    await service.send_confirmation_mail()

    token_repo.revoke_confirm_email_tokens.assert_not_awaited()
    token_repo.save_confirm_email_token.assert_not_awaited()
    mail_service.send_confirm_email_mail.assert_not_awaited()


async def test_confirm_email_confirms_user_and_revokes_tokens(
    user_service,
    unconfirmed_user,
):
    user_service.token_repo.validate_confirm_email_token.return_value = True

    result = await user_service.service.confirm_email("raw-token")

    assert result is True
    user_service.token_repo.validate_confirm_email_token.assert_awaited_once_with(
        unconfirmed_user.id,
        hash_str("raw-token"),
    )
    user_service.user_repo.confirm_email.assert_awaited_once_with(unconfirmed_user)
    user_service.token_repo.revoke_confirm_email_tokens.assert_awaited_once_with(
        unconfirmed_user.id
    )


async def test_confirm_email_raises_when_token_is_invalid(
    user_service,
):
    user_service.token_repo.validate_confirm_email_token.return_value = False

    with pytest.raises(TokenInvalid):
        await user_service.service.confirm_email("bad-token")

    user_service.user_repo.confirm_email.assert_not_awaited()
    user_service.token_repo.revoke_confirm_email_tokens.assert_not_awaited()


async def test_validate_confirm_email_token_hashes_token(
    user_service, unconfirmed_user
):
    user_service.token_repo.validate_confirm_email_token.return_value = True

    result = await user_service.service.validate_confirm_email_token("raw-token")

    assert result is True
    user_service.token_repo.validate_confirm_email_token.assert_awaited_once_with(
        unconfirmed_user.id,
        hash_str("raw-token"),
    )


async def test_update_current_user_profile_normalizes_phone(
    user_service, unconfirmed_user
):
    user_service.user_repo.update_company_user.return_value = unconfirmed_user

    result = await user_service.service.update_current_user_profile(
        first_name="Ada",
        last_name="Lovelace",
        phone_number="079 123 45 67",
    )

    assert result is unconfirmed_user
    user_service.user_repo.update_company_user.assert_awaited_once_with(
        unconfirmed_user,
        first_name="Ada",
        last_name="Lovelace",
        phone_number="+41791234567",
    )


async def test_update_current_user_profile_rejects_invalid_phone(user_service):
    with pytest.raises(PhoneNumberInvalid):
        await user_service.service.update_current_user_profile(
            first_name=None,
            last_name=None,
            phone_number="not-a-phone",
        )

    user_service.user_repo.update_company_user.assert_not_awaited()


async def test_logout_user_revokes_refresh_token(user_service, unconfirmed_user):
    await user_service.service.logout_user("refresh-token")

    user_service.token_repo.revoke_refresh_token.assert_awaited_once_with(
        unconfirmed_user.id,
        hash_str("refresh-token"),
    )


async def test_logout_user_without_token_is_noop(user_service):
    await user_service.service.logout_user(None)

    user_service.token_repo.revoke_refresh_token.assert_not_awaited()


async def test_confirm_user_rejects_non_staff_user(user_service):
    with pytest.raises(NotAllowed):
        await user_service.service.confirm_user(uuid4())

    user_service.user_repo.get_by_id.assert_not_awaited()


async def test_confirm_user_raises_when_target_missing(
    user_repo,
    token_repo,
    mail_service,
    staff_user,
):
    service = UserService(user_repo, token_repo, mail_service, staff_user)
    user_repo.get_by_id.return_value = None

    with pytest.raises(UserNotFound):
        await service.confirm_user(uuid4())

    user_repo.confirm_user.assert_not_awaited()


async def test_delete_user_rejects_staff_or_admin_target(
    user_repo,
    token_repo,
    mail_service,
    admin_user,
    staff_user,
):
    service = UserService(user_repo, token_repo, mail_service, admin_user)
    user_repo.get_by_id.return_value = staff_user

    with pytest.raises(NotAllowed):
        await service.delete_user(staff_user.id)

    user_repo.delete_user.assert_not_awaited()
