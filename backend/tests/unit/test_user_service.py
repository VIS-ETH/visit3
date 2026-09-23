from dataclasses import dataclass
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CompanyNotFound,
    EmailUsed,
    NotAllowed,
    PhoneNumberInvalid,
    UserLastCompanyMember,
    UserNotFound,
)
from app.schemas.user import UpdateCompanyUserInput, UpdateUserProfileInput
from app.services.auth_service import AuthService
from app.services.user_service import UserService


@dataclass
class UserServiceHarness:
    service: UserService
    user_repo: AsyncMock
    token_repo: AsyncMock
    company_repo: AsyncMock
    auth_service: AsyncMock
    mail_template_service: AsyncMock


@pytest.fixture
def auth_service() -> AsyncMock:
    return AsyncMock(spec=AuthService)


@pytest.fixture
def user_service(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    unconfirmed_user,
):
    return UserServiceHarness(
        service=UserService(
            user_repo,
            token_repo,
            company_repo,
            auth_service,
            mail_template_service,
            unconfirmed_user,
        ),
        user_repo=user_repo,
        token_repo=token_repo,
        company_repo=company_repo,
        auth_service=auth_service,
        mail_template_service=mail_template_service,
    )


async def test_update_current_user_profile_normalizes_phone(
    user_service, unconfirmed_user
):
    user_service.user_repo.update_user.return_value = unconfirmed_user

    result = await user_service.service.update_current_user_profile(
        UpdateUserProfileInput(
            first_name="Ada", last_name="Lovelace", phone_number="079 123 45 67"
        )
    )

    assert result is unconfirmed_user
    user_service.user_repo.update_user.assert_awaited_once()
    passed_update = user_service.user_repo.update_user.await_args.args[1]
    assert passed_update.model_dump(exclude_unset=True) == {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "phone_number": "+41791234567",
    }


async def test_update_current_user_profile_rejects_invalid_phone(user_service):
    with pytest.raises(PhoneNumberInvalid):
        await user_service.service.update_current_user_profile(
            UpdateUserProfileInput(phone_number="not-a-phone")
        )

    user_service.user_repo.update_user.assert_not_awaited()


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
    company_repo,
    auth_service,
    mail_template_service,
    staff_user,
):
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        staff_user,
    )
    user_repo.get_by_id.return_value = None

    with pytest.raises(UserNotFound):
        await service.confirm_user(uuid4())

    user_repo.confirm_user.assert_not_awaited()


async def test_update_company_user_rejects_email_of_another_user(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    admin_user,
    make_user,
):
    target = make_user(email="target@example.com")
    user_repo.get_by_id.return_value = target
    user_repo.get_by_email.return_value = make_user(email="taken@example.com")
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        admin_user,
    )

    with pytest.raises(EmailUsed):
        await service.update_company_user(
            target.id, UpdateCompanyUserInput(email="taken@example.com")
        )

    user_repo.update_user.assert_not_awaited()


async def test_update_company_user_revokes_tokens_and_resends_confirmation(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    admin_user,
    make_user,
):
    target = make_user(email="target@example.com")
    updated = make_user(email="fresh@example.com", email_confirmed=False)
    user_repo.get_by_id.return_value = target
    user_repo.get_by_email.return_value = None
    user_repo.update_user.return_value = updated
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        admin_user,
    )

    result = await service.update_company_user(
        target.id, UpdateCompanyUserInput(email="Fresh@Example.com")
    )

    assert result is updated
    token_repo.revoke_all_refresh_tokens.assert_awaited_once_with(updated.id)
    token_repo.revoke_reset_password_tokens.assert_awaited_once_with(updated.id)
    auth_service.send_confirm_email.assert_awaited_once_with(updated)


async def test_update_company_user_without_email_change_keeps_tokens(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    admin_user,
    make_user,
):
    target = make_user(email="target@example.com")
    user_repo.get_by_id.return_value = target
    user_repo.update_user.return_value = target
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        admin_user,
    )

    await service.update_company_user(
        target.id,
        UpdateCompanyUserInput(email="  Target@Example.com ", first_name="Ada"),
    )

    token_repo.revoke_all_refresh_tokens.assert_not_awaited()
    token_repo.revoke_reset_password_tokens.assert_not_awaited()
    auth_service.send_confirm_email.assert_not_awaited()


async def test_delete_user_rejects_privileged_target_for_plain_staff(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    staff_user,
    admin_user,
):
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        staff_user,
    )
    user_repo.get_by_id.return_value = admin_user

    with pytest.raises(NotAllowed):
        await service.delete_user(admin_user.id)

    user_repo.delete_user.assert_not_awaited()


async def test_delete_user_allows_an_admin_to_remove_staff(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    admin_user,
    staff_user,
):
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        admin_user,
    )
    user_repo.get_by_id.return_value = staff_user

    await service.delete_user(staff_user.id)

    user_repo.delete_user.assert_awaited_once_with(staff_user)


async def test_delete_user_rejects_deleting_yourself(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    admin_user,
):
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        admin_user,
    )

    with pytest.raises(NotAllowed):
        await service.delete_user(admin_user.id)

    user_repo.get_by_id.assert_not_awaited()
    user_repo.delete_user.assert_not_awaited()


async def test_delete_user_rejects_the_last_member_of_a_booked_company(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    staff_user,
    make_user,
):
    target = make_user(email="last@example.com", company_id=uuid4())
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        staff_user,
    )
    user_repo.get_by_id.return_value = target
    company_repo.is_last_member_of_booked_company.return_value = True

    with pytest.raises(UserLastCompanyMember):
        await service.delete_user(target.id)

    user_repo.delete_user.assert_not_awaited()


async def test_update_company_user_rejects_flag_changes_by_plain_staff(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    staff_user,
    make_user,
):
    target = make_user(email="target@example.com")
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        staff_user,
    )
    user_repo.get_by_id.return_value = target

    with pytest.raises(NotAllowed):
        await service.update_company_user(
            target.id, UpdateCompanyUserInput(is_staff=True)
        )

    user_repo.update_user.assert_not_awaited()


async def test_update_company_user_lets_staff_confirm_a_user(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    staff_user,
    make_user,
):
    target = make_user(email="target@example.com", user_confirmed=False)
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        staff_user,
    )
    user_repo.get_by_id.return_value = target
    user_repo.update_user.return_value = target

    await service.update_company_user(
        target.id, UpdateCompanyUserInput(user_confirmed=True)
    )

    passed_update = user_repo.update_user.await_args.args[1]
    assert passed_update.model_dump(exclude_unset=True) == {"user_confirmed": True}


async def test_update_company_user_rejects_an_unknown_company(
    user_repo,
    token_repo,
    company_repo,
    auth_service,
    mail_template_service,
    staff_user,
    make_user,
):
    target = make_user(email="target@example.com")
    service = UserService(
        user_repo,
        token_repo,
        company_repo,
        auth_service,
        mail_template_service,
        staff_user,
    )
    user_repo.get_by_id.return_value = target
    company_repo.get_by_id.return_value = None

    with pytest.raises(CompanyNotFound):
        await service.update_company_user(
            target.id, UpdateCompanyUserInput(company_id=uuid4())
        )

    user_repo.update_user.assert_not_awaited()
