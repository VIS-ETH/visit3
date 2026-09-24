import warnings
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.company import KpCompanyLanguage
from app.models.industry import Industry, KpCompanyProfileIndustryLink
from app.models.storage import StoredFile
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.industry_repository import IndustryRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.user_repository import UserRepository
from app.schemas.company import UpdateCompanyProfileInput


def complete_profile_input(**overrides: object) -> UpdateCompanyProfileInput:
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


async def test_complete_profile_gets_a_completion_timestamp(
    company_repository: CompanyRepository,
    user_repository: UserRepository,
):
    company = await company_repository.create_company("Acme AG")
    contact = await user_repository.create_user(
        User(email="contact@example.com", password="hash", company_id=company.id)
    )

    profile = await company_repository.upsert_kp_profile(
        company.id, complete_profile_input(kp_contact_user_id=contact.id)
    )

    assert profile.profile_completed_at is not None
    assert profile.missing_profile_fields() == []


async def test_stored_languages_are_read_back_as_enum_members(
    company_repository: CompanyRepository,
    db_session: AsyncSession,
):
    company = await company_repository.create_company("Acme AG")
    await company_repository.upsert_kp_profile(
        company.id,
        complete_profile_input(
            languages=[KpCompanyLanguage.ENGLISH, KpCompanyLanguage.GERMAN]
        ),
    )
    db_session.expunge_all()

    stored = await company_repository.get_kp_profile(company.id)

    assert stored is not None
    assert [type(language) for language in stored.languages] == [
        KpCompanyLanguage,
        KpCompanyLanguage,
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert stored.model_dump(include={"languages"})["languages"] == [
            KpCompanyLanguage.ENGLISH,
            KpCompanyLanguage.GERMAN,
        ]


async def test_industry_links_are_replaced_on_every_update(
    company_repository: CompanyRepository,
    industry_repository: IndustryRepository,
    db_session: AsyncSession,
):
    company = await company_repository.create_company("Acme AG")
    software = await industry_repository.create_industry("Software")
    banking = await industry_repository.create_industry("Banking")

    await company_repository.upsert_kp_profile(
        company.id,
        complete_profile_input(industry_ids=[software.id, banking.id, software.id]),
    )
    updated = await company_repository.upsert_kp_profile(
        company.id, complete_profile_input(industry_ids=[banking.id])
    )
    links = (
        (await db_session.execute(select(KpCompanyProfileIndustryLink))).scalars().all()
    )

    assert [link.industry.name for link in updated.industry_links] == ["Banking"]
    assert len(links) == 1


async def test_deleting_an_industry_soft_deletes_its_profile_links(
    company_repository: CompanyRepository,
    industry_repository: IndustryRepository,
):
    company = await company_repository.create_company("Acme AG")
    software = await industry_repository.create_industry("Software")
    await company_repository.upsert_kp_profile(
        company.id, complete_profile_input(industry_ids=[software.id])
    )

    await industry_repository.delete_industry(software)
    profile = await company_repository.get_kp_profile(company.id)

    assert profile is not None
    assert profile.industry_links == []
    assert await industry_repository.get_by_name("Software") is None


async def test_industry_name_is_free_again_after_a_delete(
    industry_repository: IndustryRepository,
):
    software = await industry_repository.create_industry("Software")
    await industry_repository.delete_industry(software)

    recreated = await industry_repository.create_industry("Software")

    assert recreated.id != software.id
    assert [item.name for item in await industry_repository.list_industries()] == [
        "Software"
    ]


async def test_profile_logo_is_not_cleaned_up_as_an_orphan(
    company_repository: CompanyRepository,
    kp_repository: KpRepository,
    db_session: AsyncSession,
):
    company = await company_repository.create_company("Acme AG")
    profile = await company_repository.upsert_kp_profile(
        company.id, complete_profile_input()
    )
    logo = await company_repository.upsert_stored_file(
        storage_key="company-logo.png",
        original_filename="logo.png",
        mime_type="image/png",
        size_bytes=3,
        sha256="a" * 64,
        etag=None,
    )
    orphan = await company_repository.upsert_stored_file(
        storage_key="orphan.png",
        original_filename="orphan.png",
        mime_type="image/png",
        size_bytes=3,
        sha256="b" * 64,
        etag=None,
    )
    await company_repository.set_profile_logo_stored_file_id(profile, logo.id)
    for stored_file in (logo, orphan):
        stored_file.updated_at = stored_file.updated_at - timedelta(hours=48)
        db_session.add(stored_file)
    await db_session.commit()

    orphaned = await kp_repository.list_orphaned_stored_files(max_age_hours=24)

    assert [item.storage_key for item in orphaned] == ["orphan.png"]


async def test_deleting_a_company_removes_its_profile_industry_links(
    company_repository: CompanyRepository,
    industry_repository: IndustryRepository,
    db_session: AsyncSession,
):
    company = await company_repository.create_company("Acme AG")
    software = await industry_repository.create_industry("Software")
    await company_repository.upsert_kp_profile(
        company.id, complete_profile_input(industry_ids=[software.id])
    )

    await company_repository.delete_company_keep_users(company)
    links = (
        (await db_session.execute(select(KpCompanyProfileIndustryLink))).scalars().all()
    )

    assert links == []
    assert (await db_session.execute(select(Industry))).scalars().all() != []
    assert (await db_session.execute(select(StoredFile))).scalars().all() == []
