from collections.abc import Awaitable, Callable
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.industry import Industry
from app.models.kp_event import KpBookingCompanyDetails
from app.repositories.base import rel
from tests.api.conftest import KpSetup, company_profile_payload

PROFILE = "/api/company/me/profile"


async def load_snapshot(
    db_session: AsyncSession, booking_id: str
) -> KpBookingCompanyDetails:
    statement = (
        select(KpBookingCompanyDetails)
        .where(col(KpBookingCompanyDetails.booking_id) == UUID(booking_id))
        .options(selectinload(rel(KpBookingCompanyDetails.industry_links)))
        .execution_options(populate_existing=True)
    )
    return (await db_session.execute(statement)).scalar_one()


@pytest.fixture
async def industry(db_session: AsyncSession) -> Industry:
    industry = Industry(name="Software")
    db_session.add(industry)
    await db_session.commit()
    return industry


async def register(
    client: AsyncClient,
    headers: dict[str, str],
    kp_setup: KpSetup,
    **payload: object,
) -> Response:
    return await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={"booth_zone_id": kp_setup.booth_zone_id, **payload},
        headers=headers,
    )


async def test_registration_without_confirmation_is_refused(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await complete_company_profile(company_headers)

    response = await register(client, company_headers, kp_setup)

    assert response.status_code == 400
    assert response.json()["code"] == "error.company_profile_unconfirmed"


async def test_registration_with_an_incomplete_profile_lists_the_missing_fields(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await complete_company_profile(company_headers, description="", billing_email=None)

    response = await register(client, company_headers, kp_setup, confirm_profile=True)

    assert response.status_code == 409
    assert response.json()["code"] == "error.company_profile_incomplete"
    assert response.json()["details"]["missingFields"] == [
        "description",
        "billing_email",
    ]


async def test_registration_without_a_profile_is_refused(
    client: AsyncClient, company_headers: dict[str, str], kp_setup: KpSetup
):
    response = await register(client, company_headers, kp_setup, confirm_profile=True)

    assert response.status_code == 409
    assert response.json()["code"] == "error.company_profile_incomplete"
    assert "billing_city" in response.json()["details"]["missingFields"]


async def test_snapshot_matches_the_profile_at_registration(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    industry: Industry,
):
    await client.put(
        PROFILE,
        json=company_profile_payload(
            brand_name="Acme Labs",
            website="https://acme.example",
            contact_phone="+41 44 000 00 00",
            employee_count_switzerland=12,
            employee_count_worldwide=34,
            offers_internships=True,
            offers_graduate_positions=True,
            languages=["ENGLISH", "GERMAN"],
            shipping_address="Shipping street 5",
            industry_ids=[str(industry.id)],
        ),
        headers=company_headers,
    )

    booking = await register(client, company_headers, kp_setup, confirm_profile=True)
    snapshot = await load_snapshot(db_session, booking.json()["id"])

    assert booking.status_code == 200
    assert snapshot.brand_name == "Acme Labs"
    assert snapshot.website == "https://acme.example"
    assert snapshot.contact_person == "Ada Lovelace"
    assert snapshot.contact_email == "contact@example.com"
    assert snapshot.contact_phone == "+41 44 000 00 00"
    assert snapshot.employee_count_switzerland == 12
    assert snapshot.employee_count_worldwide == 34
    assert snapshot.offers_internships is True
    assert snapshot.offers_graduate_positions is True
    assert snapshot.offers_theses is False
    assert [language.value for language in snapshot.languages] == [
        "ENGLISH",
        "GERMAN",
    ]
    assert snapshot.billing_company_name == "Acme AG"
    assert snapshot.billing_street == "Invoice street"
    assert snapshot.billing_house_number == "1"
    assert snapshot.billing_postal_code == "8000"
    assert snapshot.billing_city == "Zurich"
    assert snapshot.billing_country == "CH"
    assert snapshot.billing_email == "billing@example.com"
    assert snapshot.shipping_address == "Shipping street 5"
    assert snapshot.confirmed_at is not None
    assert [link.industry_id for link in snapshot.industry_links] == [industry.id]
    assert snapshot.industry_names == ["Software"]


async def test_snapshot_does_not_change_when_the_profile_changes_later(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    industry: Industry,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await complete_company_profile(
        company_headers, brand_name="Acme Labs", industry_ids=[str(industry.id)]
    )
    booking = await register(client, company_headers, kp_setup, confirm_profile=True)

    await complete_company_profile(
        company_headers, brand_name="Renamed Labs", billing_city="Bern", industry_ids=[]
    )
    snapshot = await load_snapshot(db_session, booking.json()["id"])
    profile = await client.get(PROFILE, headers=company_headers)

    assert profile.json()["brand_name"] == "Renamed Labs"
    assert profile.json()["billing_city"] == "Bern"
    assert profile.json()["industries"] == []
    assert snapshot.brand_name == "Acme Labs"
    assert snapshot.billing_city == "Zurich"
    assert [link.industry_id for link in snapshot.industry_links] == [industry.id]


async def test_staff_booking_marks_the_company_details_as_submitted(
    client: AsyncClient,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    listing = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings", headers=staff_headers
    )

    assert listing.json()[0]["company_details_submitted"] is True
