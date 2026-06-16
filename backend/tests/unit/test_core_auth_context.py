from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.auth_context import (
    AdminUser,
    AssignedCompanyUser,
    ConfirmedCompanyUser,
    KpPresidentUser,
    StaffUser,
    require_admin_user,
    require_assigned_company_user,
    require_confirmed_company_user,
    require_kp_president_user,
    require_staff_user,
)
from app.core.exceptions import EmailNotConfirmed, NotAllowed, UserNotConfirmed
from app.models.user import Role, User


def make_user(
    *,
    is_company: bool = True,
    email_confirmed: bool = True,
    user_confirmed: bool = True,
    company_id=None,
    is_staff: bool = False,
    is_admin: bool = False,
    roles: list[Role] | None = None,
) -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        password=None,
        is_company=is_company,
        email_confirmed=email_confirmed,
        user_confirmed=user_confirmed,
        company_id=company_id,
        is_staff=is_staff,
        is_admin=is_admin,
        roles=roles or [],
    )


def test_require_confirmed_company_user_accepts_confirmed_company_user():
    user = make_user()
    result = require_confirmed_company_user(user)

    assert isinstance(result, ConfirmedCompanyUser)
    assert result.user is user


def test_require_confirmed_company_user_rejects_non_company_user():
    user = make_user(is_company=False)

    with pytest.raises(NotAllowed):
        require_confirmed_company_user(user)


def test_require_confirmed_company_user_rejects_unconfirmed_email():
    user = make_user(email_confirmed=False)

    with pytest.raises(EmailNotConfirmed):
        require_confirmed_company_user(user)


def test_require_confirmed_company_user_rejects_unconfirmed_user():
    user = make_user(user_confirmed=False)

    with pytest.raises(UserNotConfirmed):
        require_confirmed_company_user(user)


def test_require_assigned_company_user_accepts_user_with_company():
    company_id = uuid4()
    user = make_user(company_id=company_id)

    result = require_assigned_company_user(user)

    assert isinstance(result, AssignedCompanyUser)
    assert result.company_id == company_id


def test_require_assigned_company_user_rejects_user_without_company():
    user = make_user()

    with pytest.raises(NotAllowed):
        require_assigned_company_user(user)


def test_require_staff_user_accepts_staff():
    user = make_user(is_staff=True, is_company=False)

    result = require_staff_user(user)

    assert isinstance(result, StaffUser)


def test_require_staff_user_accepts_admin():
    user = make_user(is_admin=True, is_company=False)

    result = require_staff_user(user)

    assert isinstance(result, StaffUser)


def test_require_staff_user_rejects_company_user():
    user = make_user()

    with pytest.raises(NotAllowed):
        require_staff_user(user)


def test_require_admin_user_accepts_admin():
    user = make_user(is_admin=True, is_company=False)

    result = require_admin_user(user)

    assert isinstance(result, AdminUser)


def test_require_admin_user_rejects_staff_non_admin():
    user = make_user(is_staff=True, is_company=False)

    with pytest.raises(NotAllowed):
        require_admin_user(user)


@patch("app.core.auth_context.get_settings")
def test_require_kp_president_user_accepts_matching_role(mock_get_settings):
    mock_get_settings.return_value.VISIT_KP_PRESIDENT_ROLE = "kp-president"
    user = make_user(
        is_company=False,
        roles=[Role(name="kp-president")],
    )

    result = require_kp_president_user(user)

    assert isinstance(result, KpPresidentUser)
    assert result.role == "kp-president"


@patch("app.core.auth_context.get_settings")
def test_require_kp_president_user_accepts_admin(mock_get_settings):
    mock_get_settings.return_value.VISIT_KP_PRESIDENT_ROLE = "kp-president"
    user = make_user(is_company=False, is_admin=True)

    result = require_kp_president_user(user)

    assert isinstance(result, KpPresidentUser)


@patch("app.core.auth_context.get_settings")
def test_require_kp_president_user_rejects_other_roles(mock_get_settings):
    mock_get_settings.return_value.VISIT_KP_PRESIDENT_ROLE = "kp-president"
    user = make_user(
        is_company=False,
        roles=[Role(name="other-role")],
    )

    with pytest.raises(NotAllowed):
        require_kp_president_user(user)
