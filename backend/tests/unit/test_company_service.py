from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CompanyNotFound,
    CompanyUserNotFound,
    EmailNotConfirmed,
    InviteExpired,
    InviteNotFound,
    NotAllowed,
)
from app.models.company import KpCompanyProfile
from app.services.company_service import CompanyService
from tests.unit.factories import make_invite


@dataclass
class CompanyServiceHarness:
    service: CompanyService
    company_repo: object
    mail_service: object


@pytest.fixture
def company_service(company_repo, mail_service, company_user):
    return CompanyServiceHarness(
        service=CompanyService(company_repo, mail_service, company_user),
        company_repo=company_repo,
        mail_service=mail_service,
    )


async def test_setup_company_rejects_unconfirmed_user(
    company_repo,
    mail_service,
    unconfirmed_user,
):
    service = CompanyService(company_repo, mail_service, unconfirmed_user)

    with pytest.raises(NotAllowed):
        await service.setup_company("Acme AG")

    company_repo.create_company.assert_not_awaited()
    company_repo.assign_user.assert_not_awaited()


async def test_setup_company_rejects_user_already_assigned_to_company(
    company_repo,
    mail_service,
    make_user,
):
    user = make_user(company_id=uuid4())
    service = CompanyService(company_repo, mail_service, user)

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
    mail_service,
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
    company_repo.create_invite.return_value = invite
    service = CompanyService(company_repo, mail_service, user)

    result = await service.create_invite("  Guest@Example.COM ")

    assert result is invite
    company_repo.create_invite.assert_awaited_once()
    kwargs = company_repo.create_invite.await_args.kwargs
    assert kwargs["token"] == "invite-token"
    assert kwargs["company_id"] == company.id
    assert kwargs["invited_email"] == "guest@example.com"
    assert isinstance(kwargs["expires_at"], datetime)
    mail_service.send_company_invite_mail.assert_awaited_once_with(
        "guest@example.com",
        company.name,
        "invite-token",
    )


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
            NotAllowed,
        ),
    ],
)
async def test_accept_invite_rejects_invalid_invite_cases(
    invite,
    expected_exception,
    company_repo,
    mail_service,
    company_user,
):
    company_repo.get_invite_by_token.return_value = invite
    service = CompanyService(company_repo, mail_service, company_user)

    with pytest.raises(expected_exception):
        await service.accept_invite("invite-token")

    company_repo.mark_invite_used.assert_not_awaited()
    company_repo.assign_user.assert_not_awaited()


async def test_accept_invite_rejects_unconfirmed_current_user(
    company_repo,
    mail_service,
    unconfirmed_user,
):
    service = CompanyService(company_repo, mail_service, unconfirmed_user)

    with pytest.raises(EmailNotConfirmed):
        await service.accept_invite("invite-token")

    company_repo.get_invite_by_token.assert_not_awaited()


async def test_accept_invite_rejects_already_assigned_user(
    company_repo,
    mail_service,
    make_user,
):
    user = make_user(company_id=uuid4())
    service = CompanyService(company_repo, mail_service, user)

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


async def test_get_invite_info_returns_company_name(
    company_repo,
    mail_service,
    company_user,
    make_company,
):
    company = make_company(name="VIS")
    invite = make_invite(company_id=company.id)
    company_repo.get_invite_by_token.return_value = invite
    company_repo.get_by_id.return_value = company
    service = CompanyService(company_repo, mail_service, company_user)

    result = await service.get_invite_info("invite-token")

    assert result.company_name == "VIS"


async def test_get_invite_info_rejects_missing_company(
    company_repo,
    mail_service,
    company_user,
):
    invite = make_invite()
    company_repo.get_invite_by_token.return_value = invite
    company_repo.get_by_id.return_value = None
    service = CompanyService(company_repo, mail_service, company_user)

    with pytest.raises(CompanyNotFound):
        await service.get_invite_info("invite-token")


async def test_update_company_name_delegates_to_repository(
    company_repo,
    mail_service,
    make_user,
    make_company,
):
    company = make_company(name="Old Name")
    user = make_user(company_id=company.id)
    updated = make_company(name="New Name")
    company_repo.get_by_id.return_value = company
    company_repo.update_company_name.return_value = updated
    service = CompanyService(company_repo, mail_service, user)

    result = await service.update_company_name("New Name")

    assert result is updated
    company_repo.update_company_name.assert_awaited_once_with(company, "New Name")


async def test_update_my_kp_profile_rejects_contact_user_outside_company(
    company_repo,
    mail_service,
    make_user,
):
    company_id = uuid4()
    user = make_user(company_id=company_id)
    company_repo.get_by_id.return_value = object()
    company_repo.get_users.return_value = [make_user(company_id=company_id)]
    service = CompanyService(company_repo, mail_service, user)

    with pytest.raises(CompanyUserNotFound):
        await service.update_my_kp_profile(
            invoice_address="Invoice",
            shipping_address="Shipping",
            contact_email=None,
            kp_contact_user_id=uuid4(),
        )

    company_repo.upsert_kp_profile.assert_not_awaited()


async def test_get_company_users_requires_staff_and_company_exists(
    company_repo,
    mail_service,
    staff_user,
    make_user,
):
    company_id = uuid4()
    company_repo.get_by_id.return_value = object()
    expected_user = make_user(company_id=company_id)
    company_repo.get_users.return_value = [expected_user]
    service = CompanyService(company_repo, mail_service, staff_user)

    result = await service.get_company_users(company_id)

    assert result == [expected_user]
    company_repo.get_by_id.assert_awaited_once_with(company_id)


async def test_get_company_users_raises_when_company_missing(
    company_repo,
    mail_service,
    staff_user,
):
    company_repo.get_by_id.return_value = None
    service = CompanyService(company_repo, mail_service, staff_user)

    with pytest.raises(CompanyNotFound):
        await service.get_company_users(uuid4())


async def test_get_company_with_users_returns_mapped_result(
    company_repo,
    mail_service,
    staff_user,
    make_company,
    make_user,
):
    company = make_company(name="VIS")
    company.users = [make_user(company_id=company.id)]
    company_repo.get_company_with_users.return_value = company
    service = CompanyService(company_repo, mail_service, staff_user)

    result = await service.get_company_with_users(company.id)

    assert result.id == company.id
    assert result.name == "VIS"
    assert len(result.users) == 1


async def test_get_companies_maps_repository_result(
    company_repo,
    mail_service,
    staff_user,
):
    company_repo.get_companies_with_user_counts.return_value = [
        (uuid4(), "Acme", 3),
        (uuid4(), "VIS", 5),
    ]
    service = CompanyService(company_repo, mail_service, staff_user)

    result = await service.get_companies()

    assert len(result) == 2
    assert result[0].name == "Acme"
    assert result[0].users_count == 3


async def test_delete_company_with_users_requires_admin(
    company_repo,
    mail_service,
    admin_user,
    make_company,
):
    company = make_company()
    company_repo.get_by_id.return_value = company
    service = CompanyService(company_repo, mail_service, admin_user)

    await service.delete_company_with_users(company.id)

    company_repo.delete_company_with_users.assert_awaited_once_with(company)


async def test_delete_company_keep_users_delegates_to_repository(
    company_repo,
    mail_service,
    admin_user,
    make_company,
):
    company = make_company()
    company_repo.get_by_id.return_value = company
    service = CompanyService(company_repo, mail_service, admin_user)

    await service.delete_company_keep_users(company.id)

    company_repo.delete_company_keep_users.assert_awaited_once_with(company)


async def test_remove_company_user_requires_same_company(
    company_repo,
    mail_service,
    admin_user,
    make_user,
    make_company,
):
    company = make_company()
    user = make_user(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_company_user_by_id.return_value = user
    service = CompanyService(company_repo, mail_service, admin_user)

    await service.remove_company_user(company.id, user.id)

    company_repo.remove_user_from_company.assert_awaited_once_with(user, company)


async def test_remove_company_user_raises_when_user_not_in_company(
    company_repo,
    mail_service,
    admin_user,
    make_user,
    make_company,
):
    company = make_company()
    other_company_id = uuid4()
    user = make_user(company_id=other_company_id)
    company_repo.get_by_id.return_value = company
    company_repo.get_company_user_by_id.return_value = user
    service = CompanyService(company_repo, mail_service, admin_user)

    with pytest.raises(CompanyUserNotFound):
        await service.remove_company_user(company.id, user.id)


async def test_get_my_members_returns_company_users(
    company_repo,
    mail_service,
    make_user,
    make_company,
):
    company = make_company()
    user = make_user(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_users.return_value = [user]
    service = CompanyService(company_repo, mail_service, user)

    result = await service.get_my_members()

    assert result == [user]


async def test_get_my_members_raises_when_company_missing(
    company_repo,
    mail_service,
    make_user,
):
    user = make_user(company_id=uuid4())
    company_repo.get_by_id.return_value = None
    service = CompanyService(company_repo, mail_service, user)

    with pytest.raises(CompanyNotFound):
        await service.get_my_members()


async def test_get_invite_info_rejects_expired_invite(
    company_repo,
    mail_service,
    company_user,
):
    invite = make_invite(
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    company_repo.get_invite_by_token.return_value = invite
    service = CompanyService(company_repo, mail_service, company_user)

    with pytest.raises(InviteExpired):
        await service.get_invite_info("invite-token")


async def test_get_my_kp_profile_returns_none_when_missing(
    company_repo,
    mail_service,
    make_user,
):
    company_id = uuid4()
    user = make_user(company_id=company_id)
    company_repo.get_kp_profile.return_value = None
    service = CompanyService(company_repo, mail_service, user)

    result = await service.get_my_kp_profile()

    assert result is None


async def test_update_my_kp_profile_strips_addresses_and_returns_result(
    company_repo,
    mail_service,
    make_user,
):
    company_id = uuid4()
    contact = make_user(company_id=company_id)
    user = make_user(company_id=company_id)
    profile = KpCompanyProfile(
        company_id=company_id,
        invoice_address="Invoice",
        shipping_address="Shipping",
        contact_email="contact@example.com",
        kp_contact_user_id=contact.id,
    )
    company_repo.get_by_id.return_value = object()
    company_repo.get_users.return_value = [contact]
    company_repo.upsert_kp_profile.return_value = profile
    service = CompanyService(company_repo, mail_service, user)

    result = await service.update_my_kp_profile(
        invoice_address="  Invoice  ",
        shipping_address="  Shipping  ",
        contact_email="contact@example.com",
        kp_contact_user_id=contact.id,
    )

    assert result.invoice_address == "Invoice"
    assert result.shipping_address == "Shipping"
    company_repo.upsert_kp_profile.assert_awaited_once_with(
        company_id=company_id,
        invoice_address="Invoice",
        shipping_address="Shipping",
        contact_email="contact@example.com",
        kp_contact_user_id=contact.id,
    )
