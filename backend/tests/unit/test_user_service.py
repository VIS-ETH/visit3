from dataclasses import dataclass
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    NotAllowed,
    PhoneNumberInvalid,
    UserNotFound,
)
from app.services.user_service import UserService


@dataclass
class UserServiceHarness:
    service: UserService
    user_repo: AsyncMock
    token_repo: AsyncMock


@pytest.fixture
def user_service(user_repo, token_repo, unconfirmed_user):
    return UserServiceHarness(
        service=UserService(user_repo, token_repo, unconfirmed_user),
        user_repo=user_repo,
        token_repo=token_repo,
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
        unconfirmed_user.id, "refresh-token"
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
    staff_user,
):
    service = UserService(user_repo, token_repo, staff_user)
    user_repo.get_by_id.return_value = None

    with pytest.raises(UserNotFound):
        await service.confirm_user(uuid4())

    user_repo.confirm_user.assert_not_awaited()


async def test_delete_user_rejects_staff_or_admin_target(
    user_repo,
    token_repo,
    admin_user,
    staff_user,
):
    service = UserService(user_repo, token_repo, admin_user)
    user_repo.get_by_id.return_value = staff_user

    with pytest.raises(NotAllowed):
        await service.delete_user(staff_user.id)

    user_repo.delete_user.assert_not_awaited()


async def test_get_current_user_loads_roles(user_service, unconfirmed_user):
    user_service.user_repo.load_user_roles.return_value = unconfirmed_user

    result = await user_service.service.get_current_user()

    assert result is unconfirmed_user
    user_service.user_repo.load_user_roles.assert_awaited_once_with(
        unconfirmed_user
    )


async def test_get_current_user_profile_loads_company(user_service, unconfirmed_user):
    user_service.user_repo.load_user_company.return_value = unconfirmed_user

    result = await user_service.service.get_current_user_profile()

    assert result is unconfirmed_user
    user_service.user_repo.load_user_company.assert_awaited_once_with(
        unconfirmed_user
    )


async def test_get_unconfirmed_users_requires_staff(
    user_repo,
    token_repo,
    staff_user,
):
    service = UserService(user_repo, token_repo, staff_user)
    user_repo.get_unconfirmed_users.return_value = []

    result = await service.get_unconfirmed_users()

    assert result == []
    user_repo.get_unconfirmed_users.assert_awaited_once()


async def test_confirm_user_confirms_target_user(
    user_repo,
    token_repo,
    staff_user,
    make_user,
):
    target = make_user()
    service = UserService(user_repo, token_repo, staff_user)
    user_repo.get_by_id.return_value = target
    user_repo.confirm_user.return_value = target

    result = await service.confirm_user(target.id)

    assert result is target
    user_repo.confirm_user.assert_awaited_once_with(target)


async def test_get_company_users_requires_staff(
    user_repo,
    token_repo,
    staff_user,
):
    service = UserService(user_repo, token_repo, staff_user)
    user_repo.get_company_users.return_value = []

    result = await service.get_company_users()

    assert result == []
    user_repo.get_company_users.assert_awaited_once()


async def test_get_admins_requires_staff(
    user_repo,
    token_repo,
    staff_user,
):
    service = UserService(user_repo, token_repo, staff_user)
    user_repo.get_admins.return_value = []

    result = await service.get_admins()

    assert result == []
    user_repo.get_admins.assert_awaited_once()


async def test_get_staff_requires_staff(
    user_repo,
    token_repo,
    staff_user,
):
    service = UserService(user_repo, token_repo, staff_user)
    user_repo.get_staff.return_value = []

    result = await service.get_staff()

    assert result == []
    user_repo.get_staff.assert_awaited_once()


async def test_update_company_user_requires_admin(
    user_repo,
    token_repo,
    admin_user,
    make_user,
):
    target = make_user()
    service = UserService(user_repo, token_repo, admin_user)
    user_repo.get_by_id.return_value = target
    user_repo.update_company_user.return_value = target

    result = await service.update_company_user(
        target.id,
        email="new@example.com",
        first_name="Ada",
        last_name="Lovelace",
        phone_number="079 123 45 67",
        company_id=None,
    )

    assert result is target
    user_repo.update_company_user.assert_awaited_once()
    kwargs = user_repo.update_company_user.await_args.kwargs
    assert kwargs["email"] == "new@example.com"
    assert kwargs["phone_number"] == "+41791234567"


async def test_update_company_user_rejects_invalid_phone(
    user_repo,
    token_repo,
    admin_user,
    make_user,
):
    target = make_user()
    service = UserService(user_repo, token_repo, admin_user)
    user_repo.get_by_id.return_value = target

    with pytest.raises(PhoneNumberInvalid):
        await service.update_company_user(
            target.id,
            email=None,
            first_name=None,
            last_name=None,
            phone_number="not-a-phone",
            company_id=None,
        )

    user_repo.update_company_user.assert_not_awaited()


async def test_update_company_user_raises_when_target_missing(
    user_repo,
    token_repo,
    admin_user,
):
    service = UserService(user_repo, token_repo, admin_user)
    user_repo.get_by_id.return_value = None

    with pytest.raises(UserNotFound):
        await service.update_company_user(
            uuid4(),
            email=None,
            first_name=None,
            last_name=None,
            phone_number=None,
            company_id=None,
        )


async def test_delete_user_deletes_regular_user(
    user_repo,
    token_repo,
    admin_user,
    make_user,
):
    target = make_user()
    service = UserService(user_repo, token_repo, admin_user)
    user_repo.get_by_id.return_value = target

    await service.delete_user(target.id)

    user_repo.delete_user.assert_awaited_once_with(target)


async def test_delete_user_raises_when_target_missing(
    user_repo,
    token_repo,
    admin_user,
):
    service = UserService(user_repo, token_repo, admin_user)
    user_repo.get_by_id.return_value = None

    with pytest.raises(UserNotFound):
        await service.delete_user(uuid4())

    user_repo.delete_user.assert_not_awaited()
