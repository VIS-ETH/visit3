from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.core.deleted_filter import include_deleted
from app.models.company import Company, CompanyInvite, KpCompanyProfile
from app.models.user import User


async def test_assign_user_sets_company_and_loads_relationship(
    company_repository,
    user_repository,
):
    company = await company_repository.create_company("Acme AG")
    user = await user_repository.create_user(
        User(email="member@example.com", password="hash")
    )

    result = await company_repository.assign_user(user, company.id)

    assert result.company_id == company.id
    assert result.company.name == "Acme AG"


async def test_remove_user_from_company_clears_kp_contact(
    company_repository,
    user_repository,
    db_session,
):
    company = await company_repository.create_company("Acme AG")
    user = await user_repository.create_user(
        User(email="contact@example.com", password="hash", company_id=company.id)
    )
    profile = KpCompanyProfile(
        company_id=company.id,
        invoice_address="Invoice",
        shipping_address="Shipping",
        kp_contact_user_id=user.id,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    result = await company_repository.remove_user_from_company(user, company)

    assert result.company_id is None
    refreshed_profile = await company_repository.get_kp_profile(company.id)
    assert refreshed_profile is not None
    assert refreshed_profile.kp_contact_user_id is None


async def test_invite_lifecycle(company_repository):
    company = await company_repository.create_company("Acme AG")
    invite = await company_repository.create_invite(
        token="invite-token",
        company_id=company.id,
        invited_email="guest@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    loaded = await company_repository.get_invite_by_token("invite-token")
    assert loaded == invite
    assert loaded is not None
    assert loaded.is_used is False

    await company_repository.mark_invite_used(loaded)
    used = await company_repository.get_invite_by_token("invite-token")
    assert used is not None
    assert used.is_used is True


async def test_upsert_kp_profile_creates_then_updates_profile(
    company_repository,
    user_repository,
):
    company = await company_repository.create_company("Acme AG")
    contact = await user_repository.create_user(
        User(email="contact@example.com", password="hash", company_id=company.id)
    )

    created = await company_repository.upsert_kp_profile(
        company_id=company.id,
        invoice_address="Invoice",
        shipping_address="Shipping",
        contact_email="contact@example.com",
        kp_contact_user_id=contact.id,
    )
    updated = await company_repository.upsert_kp_profile(
        company_id=company.id,
        invoice_address="Updated Invoice",
        shipping_address="Updated Shipping",
        contact_email="updated@example.com",
        kp_contact_user_id=None,
    )

    assert updated.id == created.id
    assert updated.invoice_address == "Updated Invoice"
    assert updated.shipping_address == "Updated Shipping"
    assert updated.contact_email == "updated@example.com"
    assert updated.kp_contact_user_id is None


async def test_delete_company_keep_users_soft_deletes_company_and_unassigns_users(
    company_repository,
    user_repository,
    db_session,
):
    company = await company_repository.create_company("Acme AG")
    user = await user_repository.create_user(
        User(email="member@example.com", password="hash", company_id=company.id)
    )

    await company_repository.delete_company_keep_users(company)

    assert await company_repository.get_by_id(company.id) is None
    refreshed_user = await user_repository.get_by_id(user.id)
    assert refreshed_user is not None
    assert refreshed_user.company_id is None
    result = await db_session.execute(include_deleted(select(Company)))
    deleted_company = result.scalar_one()
    assert deleted_company.deleted_at is not None


async def test_delete_company_with_users_soft_deletes_owned_rows(
    company_repository,
    user_repository,
    db_session,
):
    company = await company_repository.create_company("Acme AG")
    await user_repository.create_user(
        User(email="member@example.com", password="hash", company_id=company.id)
    )
    await company_repository.create_invite(
        token="invite-token",
        company_id=company.id,
        invited_email="guest@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    profile = KpCompanyProfile(
        company_id=company.id,
        invoice_address="Invoice",
        shipping_address="Shipping",
    )
    db_session.add(profile)
    await db_session.commit()

    await company_repository.delete_company_with_users(company)

    assert await company_repository.get_by_id(company.id) is None
    assert await user_repository.get_by_email("member@example.com") is None
    result = await db_session.execute(include_deleted(select(CompanyInvite)))
    deleted_invite = result.scalar_one()
    assert deleted_invite.deleted_at is not None
