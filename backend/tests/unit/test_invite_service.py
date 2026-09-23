from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CompanyNotFound,
    InviteEmailMismatch,
    InviteExpired,
    InviteNotFound,
)
from app.models.company import CompanyInvite
from app.services.invite_service import InviteService


def make_invite(
    *,
    token: str = "invite-token",
    company_id=None,
    invited_email: str = "user@example.com",
    is_used: bool = False,
    expires_at: datetime | None = None,
) -> CompanyInvite:
    return CompanyInvite(
        token=token,
        company_id=company_id or uuid4(),
        invited_email=invited_email,
        is_used=is_used,
        expires_at=expires_at or datetime.now(timezone.utc) + timedelta(days=1),
    )


@pytest.fixture
def invites(company_repo) -> InviteService:
    return InviteService(company_repo)


@pytest.mark.parametrize(
    ("invite", "expected_exception"),
    [
        (None, InviteNotFound),
        (make_invite(is_used=True), InviteNotFound),
        (
            make_invite(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)),
            InviteExpired,
        ),
    ],
)
async def test_load_open_invite_rejects_unusable_invites(
    invites, company_repo, invite, expected_exception
):
    company_repo.get_invite_by_token.return_value = invite

    with pytest.raises(expected_exception):
        await invites.load_open_invite("invite-token", "action")


async def test_get_invite_info_reports_an_existing_account(
    invites, company_repo, make_company, make_user
):
    company = make_company(name="VIS")
    company_repo.get_invite_by_token.return_value = make_invite(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_user_by_email.return_value = make_user()

    result = await invites.get_invite_info("invite-token")

    assert result.company_name == "VIS"
    assert result.account_exists is True


async def test_get_invite_info_reports_a_missing_account(
    invites, company_repo, make_company
):
    company = make_company(name="VIS")
    company_repo.get_invite_by_token.return_value = make_invite(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_user_by_email.return_value = None

    result = await invites.get_invite_info("invite-token")

    assert result.account_exists is False


async def test_get_invite_info_rejects_missing_company(invites, company_repo):
    company_repo.get_invite_by_token.return_value = make_invite()
    company_repo.get_by_id.return_value = None

    with pytest.raises(CompanyNotFound):
        await invites.get_invite_info("invite-token")


async def test_join_company_marks_the_invite_used_and_assigns_the_user(
    invites, company_repo, company_user
):
    company_id = uuid4()
    invite = make_invite(company_id=company_id, invited_email=company_user.email)
    company_repo.get_invite_by_token.return_value = invite
    company_repo.assign_user.return_value = company_user

    result = await invites.join_company(company_user, "invite-token", "action")

    assert result is company_user
    company_repo.mark_invite_used.assert_awaited_once_with(invite)
    company_repo.assign_user.assert_awaited_once_with(company_user, company_id)


async def test_join_company_rejects_a_foreign_email(
    invites, company_repo, company_user
):
    company_repo.get_invite_by_token.return_value = make_invite(
        invited_email="someone-else@example.com"
    )

    with pytest.raises(InviteEmailMismatch):
        await invites.join_company(company_user, "invite-token", "action")

    company_repo.mark_invite_used.assert_not_awaited()
    company_repo.assign_user.assert_not_awaited()
