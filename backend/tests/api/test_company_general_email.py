from collections.abc import Awaitable, Callable
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.company import KpCompanyProfile
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from tests.api.conftest import company_profile_payload, first_member_id

PROFILE = "/api/company/me/profile"
ERROR_CODE = "error.company_general_email_is_login"
LOGIN_EMAIL = "company@example.com"
MEMBER_EMAIL = "colleague@example.com"


@pytest.fixture
async def colleague(
    db_session: AsyncSession,
    create_user: Callable[..., Awaitable[User]],
    company_user: User,
) -> User:
    user = await create_user(email=MEMBER_EMAIL)
    return await CompanyRepository(db_session).assign_user(
        user, UUID(str(company_user.company_id))
    )


async def save_profile(
    client: AsyncClient,
    headers: dict[str, str],
    **overrides: object,
):
    payload = company_profile_payload(
        kp_contact_user_id=await first_member_id(client, headers), **overrides
    )
    return await client.put(PROFILE, json=payload, headers=headers)


async def store_general_email(
    db_session: AsyncSession, company_id: UUID | None, general_email: str
) -> None:
    statement = select(KpCompanyProfile).where(
        col(KpCompanyProfile.company_id) == company_id
    )
    profile = (await db_session.execute(statement)).scalar_one()
    profile.general_email = general_email
    db_session.add(profile)
    await db_session.commit()


@pytest.mark.parametrize(
    "general_email",
    [LOGIN_EMAIL, "Company@Example.com", "  COMPANY@example.COM  "],
)
async def test_the_own_login_email_is_rejected(
    client: AsyncClient, company_headers: dict[str, str], general_email: str
):
    response = await save_profile(client, company_headers, general_email=general_email)

    assert response.status_code == 400
    assert response.json()["code"] == ERROR_CODE


async def test_the_login_email_of_another_member_is_rejected(
    client: AsyncClient, company_headers: dict[str, str], colleague: User
):
    response = await save_profile(
        client, company_headers, general_email=MEMBER_EMAIL.upper()
    )

    assert response.status_code == 400
    assert response.json()["code"] == ERROR_CODE


async def test_a_different_address_is_accepted(
    client: AsyncClient, company_headers: dict[str, str], colleague: User
):
    response = await save_profile(
        client, company_headers, general_email="info@example.com"
    )

    assert response.status_code == 200
    assert response.json()["general_email"] == "info@example.com"


async def test_the_login_email_of_another_company_is_accepted(
    client: AsyncClient,
    company_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
):
    await create_user(email="outsider@example.com", company_name="Other AG")

    response = await save_profile(
        client, company_headers, general_email="outsider@example.com"
    )

    assert response.status_code == 200


async def test_staff_cannot_set_a_login_email(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
):
    await save_profile(client, company_headers)

    response = await client.put(
        f"/api/company/{company_user.company_id}/profile",
        json=company_profile_payload(
            kp_contact_user_id=str(company_user.id), general_email=LOGIN_EMAIL
        ),
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == ERROR_CODE


async def test_a_stored_login_email_does_not_block_other_changes(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    company_headers: dict[str, str],
):
    await save_profile(client, company_headers)
    await store_general_email(db_session, company_user.company_id, LOGIN_EMAIL)

    response = await save_profile(
        client, company_headers, general_email=LOGIN_EMAIL, billing_city="Bern"
    )

    assert response.status_code == 200
    assert response.json()["billing_city"] == "Bern"
    assert response.json()["general_email"] == LOGIN_EMAIL
    assert response.json()["profile_complete"] is True
    assert response.json()["missing_profile_fields"] == []


async def test_staff_may_keep_a_stored_login_email(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
):
    await save_profile(client, company_headers)
    await store_general_email(db_session, company_user.company_id, LOGIN_EMAIL)

    response = await client.put(
        f"/api/company/{company_user.company_id}/profile",
        json=company_profile_payload(
            kp_contact_user_id=str(company_user.id),
            general_email=LOGIN_EMAIL,
            billing_city="Bern",
        ),
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["billing_city"] == "Bern"


async def test_switching_a_stored_login_email_to_another_login_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    company_headers: dict[str, str],
    colleague: User,
):
    await save_profile(client, company_headers)
    await store_general_email(db_session, company_user.company_id, LOGIN_EMAIL)

    response = await save_profile(client, company_headers, general_email=MEMBER_EMAIL)

    assert response.status_code == 400
    assert response.json()["code"] == ERROR_CODE


async def test_a_stored_login_email_is_not_reported_as_missing(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    company_headers: dict[str, str],
):
    await save_profile(client, company_headers)
    await store_general_email(db_session, company_user.company_id, LOGIN_EMAIL)

    profile = await client.get(PROFILE, headers=company_headers)
    company = await client.get("/api/company/me", headers=company_headers)

    assert profile.json()["missing_profile_fields"] == []
    assert company.json()["profile_complete"] is True
