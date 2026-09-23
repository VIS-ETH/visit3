from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CompanyHasUpcomingBookings,
    CompanyInvitePending,
    EmailNotConfirmed,
    InviteEmailMismatch,
    InviteExpired,
    InviteNotFound,
    NotAllowed,
    UserAlreadyInCompany,
    UserLastCompanyMember,
)
from app.mail_templates.keys import MailTemplateKey
from app.models.company import CompanyInvite
from app.services.company_service import CompanyService


@dataclass
class CompanyServiceHarness:
    service: CompanyService
    company_repo: object
    mail_template_service: object


@pytest.fixture
def company_service(company_repo, mail_template_service, storage_service, company_user):
    return CompanyServiceHarness(
        service=CompanyService(
            company_repo, mail_template_service, storage_service, company_user
        ),
        company_repo=company_repo,
        mail_template_service=mail_template_service,
    )


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


async def test_setup_company_rejects_unconfirmed_user(
    company_repo,
    mail_template_service,
    storage_service,
    unconfirmed_user,
):
    service = CompanyService(
        company_repo, mail_template_service, storage_service, unconfirmed_user
    )

    with pytest.raises(NotAllowed):
        await service.setup_company("Acme AG")

    company_repo.create_company.assert_not_awaited()
    company_repo.assign_user.assert_not_awaited()


async def test_setup_company_rejects_user_already_assigned_to_company(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
):
    user = make_user(company_id=uuid4())
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    with pytest.raises(NotAllowed):
        await service.setup_company("Acme AG")

    company_repo.create_company.assert_not_awaited()
    company_repo.assign_user.assert_not_awaited()


async def test_setup_company_rejects_blank_name(company_service):
    company_service.company_repo.get_by_name.return_value = None

    with pytest.raises(NotAllowed):
        await company_service.service.setup_company("   ")

    company_service.company_repo.create_company.assert_not_awaited()
    company_service.company_repo.assign_user.assert_not_awaited()


async def test_setup_company_creates_company_and_assigns_user(
    company_service,
    make_company,
):
    company = make_company(name="Acme AG")
    company_service.company_repo.get_by_name.return_value = None
    company_service.company_repo.create_company.return_value = company

    result = await company_service.service.setup_company("  Acme AG  ")

    assert result is company
    company_service.company_repo.get_by_name.assert_awaited_once_with("Acme AG")
    company_service.company_repo.create_company.assert_awaited_once_with("Acme AG")
    company_service.company_repo.assign_user.assert_awaited_once_with(
        company_service.service.current_user,
        company.id,
    )


async def test_create_invite_normalizes_email_creates_invite_and_sends_mail(
    monkeypatch,
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
    make_company,
):
    company = make_company(name="Acme AG")
    user = make_user(company_id=company.id)
    invite = make_invite(
        token="invite-token",
        company_id=company.id,
        invited_email="guest@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    monkeypatch.setattr(
        "app.services.company_service.secrets.token_urlsafe",
        lambda length: "invite-token",
    )
    company_repo.get_by_id.return_value = company
    company_repo.get_pending_invite.return_value = None
    company_repo.create_invite.return_value = invite
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    result = await service.create_invite("  Guest@Example.COM ")

    assert result is invite
    company_repo.create_invite.assert_awaited_once()
    kwargs = company_repo.create_invite.await_args.kwargs
    assert kwargs["token"] == "invite-token"
    assert kwargs["company_id"] == company.id
    assert kwargs["invited_email"] == "guest@example.com"
    assert isinstance(kwargs["expires_at"], datetime)
    mail_template_service.send.assert_awaited_once()
    key, recipients, context = mail_template_service.send.await_args.args
    assert key == MailTemplateKey.COMPANY_INVITE
    assert recipients == ["guest@example.com"]
    assert context.company_name == company.name
    assert context.invite_url.endswith(
        "/company/join/invite-token?email=guest%40example.com"
    )


async def test_create_invite_refuses_a_pending_invite(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
    make_company,
):
    company = make_company(name="Acme AG")
    user = make_user(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_pending_invite.return_value = make_invite(
        token="pending-token",
        company_id=company.id,
        invited_email="guest@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    with pytest.raises(CompanyInvitePending):
        await service.create_invite("  Guest@Example.COM ")

    company_repo.create_invite.assert_not_awaited()
    mail_template_service.send.assert_not_awaited()


@pytest.mark.parametrize(
    ("invite", "expected_exception"),
    [
        (None, InviteNotFound),
        (
            make_invite(
                token="used-token",
                is_used=True,
            ),
            InviteNotFound,
        ),
        (
            make_invite(
                token="expired-token",
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            ),
            InviteExpired,
        ),
        (
            make_invite(
                token="wrong-email-token",
                invited_email="other@example.com",
            ),
            InviteEmailMismatch,
        ),
    ],
)
async def test_accept_invite_rejects_invalid_invite_cases(
    invite,
    expected_exception,
    company_repo,
    mail_template_service,
    storage_service,
    company_user,
):
    company_repo.get_invite_by_token.return_value = invite
    service = CompanyService(
        company_repo, mail_template_service, storage_service, company_user
    )

    with pytest.raises(expected_exception):
        await service.accept_invite("invite-token")

    company_repo.mark_invite_used.assert_not_awaited()
    company_repo.assign_user.assert_not_awaited()


async def test_accept_invite_rejects_unconfirmed_current_user(
    company_repo,
    mail_template_service,
    storage_service,
    unconfirmed_user,
):
    service = CompanyService(
        company_repo, mail_template_service, storage_service, unconfirmed_user
    )

    with pytest.raises(EmailNotConfirmed):
        await service.accept_invite("invite-token")

    company_repo.get_invite_by_token.assert_not_awaited()


async def test_accept_invite_rejects_already_assigned_user(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
):
    user = make_user(company_id=uuid4())
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    with pytest.raises(NotAllowed):
        await service.accept_invite("invite-token")

    company_repo.get_invite_by_token.assert_not_awaited()


async def test_accept_invite_marks_invite_used_and_assigns_user(
    company_service,
    company_user,
):
    company_id = uuid4()
    invite = make_invite(
        company_id=company_id,
        invited_email=company_user.email,
    )
    company_service.company_repo.get_invite_by_token.return_value = invite
    company_service.company_repo.assign_user.return_value = company_user

    result = await company_service.service.accept_invite("invite-token")

    assert result is company_user
    company_service.company_repo.mark_invite_used.assert_awaited_once_with(invite)
    company_service.company_repo.assign_user.assert_awaited_once_with(
        company_user,
        company_id,
    )


@pytest.mark.parametrize(
    "delete_method",
    ["delete_company_with_users", "delete_company_keep_users"],
)
async def test_delete_company_refuses_while_upcoming_bookings_exist(
    delete_method,
    company_repo,
    mail_template_service,
    storage_service,
    admin_user,
    make_company,
):
    company = make_company()
    company_repo.get_by_id.return_value = company
    company_repo.has_bookings_for_upcoming_events.return_value = True
    service = CompanyService(
        company_repo, mail_template_service, storage_service, admin_user
    )

    with pytest.raises(CompanyHasUpcomingBookings):
        await getattr(service, delete_method)(company.id)

    getattr(company_repo, delete_method).assert_not_awaited()


@pytest.mark.parametrize(
    "delete_method",
    ["delete_company_with_users", "delete_company_keep_users"],
)
async def test_delete_company_proceeds_without_upcoming_bookings(
    delete_method,
    company_repo,
    mail_template_service,
    storage_service,
    admin_user,
    make_company,
):
    company = make_company()
    company_repo.get_by_id.return_value = company
    company_repo.has_bookings_for_upcoming_events.return_value = False
    service = CompanyService(
        company_repo, mail_template_service, storage_service, admin_user
    )

    await getattr(service, delete_method)(company.id)

    getattr(company_repo, delete_method).assert_awaited_once_with(company)


async def test_update_company_name_delegates_to_repository(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
    make_company,
):
    company = make_company(name="Old Name")
    user = make_user(company_id=company.id)
    updated = make_company(name="New Name")
    company_repo.get_by_id.return_value = company
    company_repo.get_by_name.return_value = None
    company_repo.update_company_name.return_value = updated
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    result = await service.update_company_name("  New Name  ")

    assert result is updated
    company_repo.update_company_name.assert_awaited_once_with(company, "New Name")


async def test_update_company_name_rejects_name_of_another_company(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
    make_company,
):
    company = make_company(name="Old Name")
    user = make_user(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_by_name.return_value = make_company(name="New Name")
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    with pytest.raises(NotAllowed):
        await service.update_company_name("New Name")

    company_repo.update_company_name.assert_not_awaited()


async def test_update_company_name_allows_keeping_own_name(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
    make_company,
):
    company = make_company(name="Acme AG")
    user = make_user(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_by_name.return_value = company
    company_repo.update_company_name.return_value = company
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    result = await service.update_company_name("Acme AG")

    assert result is company
    company_repo.update_company_name.assert_awaited_once_with(company, "Acme AG")


async def test_update_company_renames_any_company_for_staff(
    company_repo,
    mail_template_service,
    storage_service,
    staff_user,
    make_company,
):
    company = make_company(name="Old Name")
    updated = make_company(name="New Name")
    company_repo.get_by_id.return_value = company
    company_repo.get_by_name.return_value = None
    company_repo.update_company_name.return_value = updated
    service = CompanyService(
        company_repo, mail_template_service, storage_service, staff_user
    )

    result = await service.update_company(company.id, "  New Name  ")

    assert result is updated
    company_repo.update_company_name.assert_awaited_once_with(company, "New Name")


async def test_update_company_rejects_a_taken_name(
    company_repo,
    mail_template_service,
    storage_service,
    staff_user,
    make_company,
):
    company = make_company(name="Old Name")
    company_repo.get_by_id.return_value = company
    company_repo.get_by_name.return_value = make_company(name="New Name")
    service = CompanyService(
        company_repo, mail_template_service, storage_service, staff_user
    )

    with pytest.raises(NotAllowed):
        await service.update_company(company.id, "New Name")

    company_repo.update_company_name.assert_not_awaited()


async def test_update_company_rejects_a_company_user(
    company_repo,
    mail_template_service,
    storage_service,
    company_user,
    make_company,
):
    company = make_company()
    service = CompanyService(
        company_repo, mail_template_service, storage_service, company_user
    )

    with pytest.raises(NotAllowed):
        await service.update_company(company.id, "New Name")

    company_repo.update_company_name.assert_not_awaited()


async def test_remove_company_user_refuses_the_last_booked_member(
    company_repo,
    mail_template_service,
    storage_service,
    staff_user,
    make_user,
    make_company,
):
    company = make_company()
    member = make_user(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_company_user_by_id.return_value = member
    company_repo.is_last_member_of_booked_company.return_value = True
    service = CompanyService(
        company_repo, mail_template_service, storage_service, staff_user
    )

    with pytest.raises(UserLastCompanyMember):
        await service.remove_company_user(company.id, member.id)

    company_repo.remove_user_from_company.assert_not_awaited()


async def test_remove_company_user_detaches_the_member_for_staff(
    company_repo,
    mail_template_service,
    storage_service,
    staff_user,
    make_user,
    make_company,
):
    company = make_company()
    member = make_user(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_company_user_by_id.return_value = member
    company_repo.is_last_member_of_booked_company.return_value = False
    service = CompanyService(
        company_repo, mail_template_service, storage_service, staff_user
    )

    await service.remove_company_user(company.id, member.id)

    company_repo.remove_user_from_company.assert_awaited_once_with(member, company)


async def test_add_company_user_assigns_an_unassigned_user(
    company_repo,
    mail_template_service,
    storage_service,
    staff_user,
    make_user,
    make_company,
):
    company = make_company()
    user = make_user()
    company_repo.get_by_id.return_value = company
    company_repo.get_company_user_by_id.return_value = user
    company_repo.assign_user.return_value = user
    service = CompanyService(
        company_repo, mail_template_service, storage_service, staff_user
    )

    result = await service.add_company_user(company.id, user.id)

    assert result is user
    company_repo.assign_user.assert_awaited_once_with(user, company.id)


async def test_add_company_user_rejects_a_user_with_a_company(
    company_repo,
    mail_template_service,
    storage_service,
    staff_user,
    make_user,
    make_company,
):
    company = make_company()
    user = make_user(company_id=uuid4())
    company_repo.get_by_id.return_value = company
    company_repo.get_company_user_by_id.return_value = user
    service = CompanyService(
        company_repo, mail_template_service, storage_service, staff_user
    )

    with pytest.raises(UserAlreadyInCompany):
        await service.add_company_user(company.id, user.id)

    company_repo.assign_user.assert_not_awaited()


async def test_add_company_user_rejects_a_staff_target(
    company_repo,
    mail_template_service,
    storage_service,
    staff_user,
    make_company,
):
    company = make_company()
    company_repo.get_by_id.return_value = company
    company_repo.get_company_user_by_id.return_value = staff_user
    service = CompanyService(
        company_repo, mail_template_service, storage_service, staff_user
    )

    with pytest.raises(NotAllowed):
        await service.add_company_user(company.id, staff_user.id)

    company_repo.assign_user.assert_not_awaited()


async def test_search_companies_reports_counts_and_paging(
    company_repo,
    mail_template_service,
    storage_service,
    staff_user,
    make_company,
):
    company = make_company(name="Acme AG")
    company_repo.count_companies.return_value = 3
    company_repo.get_company_overviews.return_value = [(company.id, company.name, 2, 1)]
    service = CompanyService(
        company_repo, mail_template_service, storage_service, staff_user
    )

    result = await service.search_companies("acme", 2, 10)

    assert result.total == 3
    assert result.page == 2
    assert result.page_size == 10
    assert [
        (item.name, item.users_count, item.bookings_count) for item in result.items
    ] == [("Acme AG", 2, 1)]
    company_repo.get_company_overviews.assert_awaited_once_with("acme", 10, 10)
