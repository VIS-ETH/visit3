from collections.abc import Callable
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CompanyNotFound,
    CompanyUserNotFound,
    EmailNotConfirmed,
    IndustryNotFound,
    NotAllowed,
)
from app.models.company import MANDATORY_PROFILE_FIELDS, KpCompanyProfile
from app.models.industry import Industry
from app.models.user import User
from app.schemas.company import UpdateCompanyProfileInput
from app.services.company_service import CompanyService


def make_profile_input(**overrides: object) -> UpdateCompanyProfileInput:
    values: dict[str, object] = {
        "description": "We build the best anvils in Switzerland.",
        "general_email": "info@example.com",
        "billing_company_name": "Acme AG",
        "billing_street": "Invoice street",
        "billing_postal_code": "8000",
        "billing_city": "Zurich",
        "billing_country": "CH",
        "billing_email": "billing@example.com",
        **overrides,
    }
    return UpdateCompanyProfileInput(**values)


def test_missing_profile_fields_lists_every_mandatory_field_of_an_empty_profile():
    profile = KpCompanyProfile(company_id=uuid4())

    assert profile.missing_profile_fields() == list(MANDATORY_PROFILE_FIELDS)
    assert profile.is_complete is False


def test_missing_profile_fields_ignores_blank_values():
    profile = KpCompanyProfile(
        company_id=uuid4(),
        **make_profile_input(billing_city="   ").model_dump(exclude={"industry_ids"}),
    )

    assert profile.missing_profile_fields() == ["kp_contact_user_id", "billing_city"]


def test_missing_profile_fields_is_empty_for_a_complete_profile():
    profile = KpCompanyProfile(
        company_id=uuid4(),
        **make_profile_input(kp_contact_user_id=uuid4()).model_dump(
            exclude={"industry_ids"}
        ),
    )

    assert profile.missing_profile_fields() == []
    assert profile.is_complete is True


def test_billing_country_is_normalized_to_upper_case():
    assert make_profile_input(billing_country="ch").billing_country == "CH"


def test_billing_country_rejects_values_that_are_not_alpha_2():
    with pytest.raises(ValueError):
        make_profile_input(billing_country="CHE")


async def test_get_my_company_reports_the_missing_fields(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
    make_company,
):
    company = make_company()
    user = make_user(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_kp_profile.return_value = None
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    result = await service.get_my_company()

    assert result.profile_complete is False
    assert result.missing_profile_fields == list(MANDATORY_PROFILE_FIELDS)


async def test_get_my_profile_returns_an_empty_profile_without_creating_one(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
):
    company_id = uuid4()
    user = make_user(company_id=company_id)
    company_repo.get_kp_profile.return_value = None
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    result = await service.get_my_profile()

    assert result.id is None
    assert result.company_id == company_id
    assert result.missing_profile_fields == list(MANDATORY_PROFILE_FIELDS)
    company_repo.upsert_kp_profile.assert_not_awaited()


async def test_update_my_profile_rejects_a_contact_user_outside_the_company(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
    make_company,
):
    company = make_company()
    user = make_user(company_id=company.id)
    company_repo.get_by_id.return_value = company
    company_repo.get_users.return_value = [user]
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    with pytest.raises(CompanyUserNotFound):
        await service.update_my_profile(make_profile_input(kp_contact_user_id=uuid4()))

    company_repo.upsert_kp_profile.assert_not_awaited()


async def test_update_my_profile_returns_the_contact_member(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
    make_company,
    make_company_profile: Callable[..., KpCompanyProfile],
):
    company = make_company()
    user = make_user(company_id=company.id)
    user.first_name = "Ada"
    user.phone_number = "+41 44 000 00 00"
    profile = make_company_profile(company_id=company.id, kp_contact_user_id=user.id)
    profile.kp_contact_user = user
    company_repo.get_by_id.return_value = company
    company_repo.get_users.return_value = [user]
    company_repo.upsert_kp_profile.return_value = profile
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    result = await service.update_my_profile(
        make_profile_input(kp_contact_user_id=user.id)
    )

    assert result.kp_contact_user_id == user.id
    assert result.kp_contact_user is not None
    assert result.kp_contact_user.first_name == "Ada"
    assert result.kp_contact_user.email == user.email
    assert result.kp_contact_user.phone_number == "+41 44 000 00 00"


async def test_update_my_profile_rejects_an_unknown_industry(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
):
    user = make_user(company_id=uuid4())
    company_repo.get_industries_by_ids.return_value = []
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    with pytest.raises(IndustryNotFound):
        await service.update_my_profile(make_profile_input(industry_ids=[uuid4()]))

    company_repo.upsert_kp_profile.assert_not_awaited()


async def test_update_my_profile_returns_the_stored_industries(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
    make_company_profile: Callable[..., KpCompanyProfile],
):
    company_id = uuid4()
    user = make_user(company_id=company_id)
    industry = Industry(id=uuid4(), name="Software")
    profile = make_company_profile(company_id=company_id)
    profile.industry_links = []
    company_repo.get_industries_by_ids.return_value = [industry]
    company_repo.upsert_kp_profile.return_value = profile
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    result = await service.update_my_profile(
        make_profile_input(industry_ids=[industry.id])
    )

    assert result.profile_complete is True
    assert result.missing_profile_fields == []
    company_repo.upsert_kp_profile.assert_awaited_once()


async def test_profile_routes_reject_a_user_without_a_confirmed_email(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
):
    user: User = make_user(company_id=uuid4(), email_confirmed=False)
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    with pytest.raises(EmailNotConfirmed):
        await service.get_my_profile()


async def test_profile_routes_reject_a_user_without_a_company(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
):
    service = CompanyService(
        company_repo, mail_template_service, storage_service, make_user()
    )

    with pytest.raises(NotAllowed):
        await service.get_my_profile()


async def test_staff_profile_update_rejects_an_unknown_company(
    company_repo,
    mail_template_service,
    storage_service,
    staff_user,
):
    company_repo.get_by_id.return_value = None
    service = CompanyService(
        company_repo, mail_template_service, storage_service, staff_user
    )

    with pytest.raises(CompanyNotFound):
        await service.update_company_profile(uuid4(), make_profile_input())


async def test_staff_profile_update_is_refused_for_company_users(
    company_repo,
    mail_template_service,
    storage_service,
    make_user,
):
    user = make_user(company_id=uuid4())
    service = CompanyService(company_repo, mail_template_service, storage_service, user)

    with pytest.raises(NotAllowed):
        await service.update_company_profile(uuid4(), make_profile_input())
