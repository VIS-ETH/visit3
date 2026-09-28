from collections.abc import Awaitable, Callable
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.kp_event import KpBookingCompanyDetails
from app.models.user import User
from tests.api.conftest import KpSetup, company_profile_payload, first_member_id

PROFILE = "/api/company/me/profile"
STUDENT_EMAIL = "jobs@acme.example"


async def save_profile(
    client: AsyncClient, headers: dict[str, str], **overrides: object
) -> Response:
    payload = company_profile_payload(
        kp_contact_user_id=await first_member_id(client, headers), **overrides
    )
    return await client.put(PROFILE, json=payload, headers=headers)


async def booking_details(
    db_session: AsyncSession, booking_id: str
) -> KpBookingCompanyDetails:
    statement = (
        select(KpBookingCompanyDetails)
        .where(col(KpBookingCompanyDetails.booking_id) == UUID(booking_id))
        .execution_options(populate_existing=True)
    )
    return (await db_session.execute(statement)).scalar_one()


async def test_a_profile_without_a_student_email_is_complete(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await save_profile(client, company_headers)

    assert response.status_code == 200
    assert response.json()["student_contact_email"] is None
    assert response.json()["profile_complete"] is True
    assert response.json()["missing_profile_fields"] == []


async def test_the_student_email_is_stored_trimmed(
    client: AsyncClient, company_headers: dict[str, str]
):
    saved = await save_profile(
        client, company_headers, student_contact_email=f"  {STUDENT_EMAIL}  "
    )
    loaded = await client.get(PROFILE, headers=company_headers)

    assert saved.status_code == 200
    assert loaded.json()["student_contact_email"] == STUDENT_EMAIL


@pytest.mark.parametrize(
    "invalid", ["not-an-email", "jobs@", "@acme.example", "jobs acme@example.ch"]
)
async def test_an_invalid_student_email_is_rejected(
    client: AsyncClient, company_headers: dict[str, str], invalid: str
):
    response = await save_profile(
        client, company_headers, student_contact_email=invalid
    )

    assert response.status_code == 422


async def test_the_student_email_can_be_removed(
    client: AsyncClient, company_headers: dict[str, str]
):
    await save_profile(client, company_headers, student_contact_email=STUDENT_EMAIL)

    response = await save_profile(client, company_headers, student_contact_email=None)

    assert response.status_code == 200
    assert response.json()["student_contact_email"] is None


async def test_staff_can_set_the_student_email(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
):
    await save_profile(client, company_headers)

    written = await client.put(
        f"/api/company/{company_user.company_id}/profile",
        json=company_profile_payload(
            kp_contact_user_id=str(company_user.id),
            student_contact_email=STUDENT_EMAIL,
        ),
        headers=staff_headers,
    )
    company_view = await client.get(PROFILE, headers=company_headers)

    assert written.status_code == 200
    assert company_view.json()["student_contact_email"] == STUDENT_EMAIL


async def test_a_booking_without_a_student_email_is_accepted(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    response = await register_booking(company_headers, kp_setup)

    assert response.status_code == 200
    assert response.json()["missing_items"] == []


async def test_the_booking_snapshot_keeps_the_student_email(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
):
    await save_profile(client, company_headers, student_contact_email=STUDENT_EMAIL)

    booking = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={
            "booth_zone_id": kp_setup.booth_zone_id,
            "services": [],
            "confirm_profile": True,
        },
        headers=company_headers,
    )

    details = await booking_details(db_session, booking.json()["id"])
    assert details.student_contact_email == STUDENT_EMAIL


async def test_a_student_email_added_later_fills_the_booking_snapshot(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)

    await save_profile(client, company_headers, student_contact_email=STUDENT_EMAIL)

    details = await booking_details(db_session, booking.json()["id"])
    assert details.student_contact_email == STUDENT_EMAIL
