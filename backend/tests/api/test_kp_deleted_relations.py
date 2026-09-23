from collections.abc import Awaitable, Callable
from uuid import UUID

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.company import Company
from tests.api.conftest import KpSetup

BOOKINGS_EXPORT = "exports/bookings/download"
REQUIREMENTS_EXPORT = "exports/service-requirements/download"
COMPANY_DETAILS_EXPORT = "exports/company-details/download"


async def cancel_booking(
    client: AsyncClient, company_headers: dict[str, str], booking_id: str
) -> Response:
    return await client.patch(
        f"/api/kp/bookings/{booking_id}/status",
        json={"status": "CANCELLED"},
        headers=company_headers,
    )


async def soft_delete_company(db_session: AsyncSession, company_id: UUID) -> None:
    statement = select(Company).where(col(Company.id) == company_id)
    company = (await db_session.execute(statement)).scalar_one()
    company.mark_deleted()
    db_session.add(company)
    await db_session.commit()


async def test_staff_sees_zone_of_cancelled_booking_in_deleted_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)
    cancelled = await cancel_booking(client, company_headers, booking.json()["id"])
    deleted = await client.delete(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}", headers=staff_headers
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings", headers=staff_headers
    )

    assert cancelled.status_code == 200
    assert deleted.status_code == 200
    assert response.status_code == 200
    assert [entry["booth_zone"]["name"] for entry in response.json()] == ["Main hall"]


async def test_staff_booking_detail_keeps_the_deleted_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)
    booking_id = booking.json()["id"]
    await cancel_booking(client, company_headers, booking_id)
    await client.delete(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}", headers=staff_headers
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{booking_id}",
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["booth_zone"]["name"] == "Main hall"


async def test_exports_still_render_bookings_in_a_deleted_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)
    await cancel_booking(client, company_headers, booking.json()["id"])
    await client.delete(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}", headers=staff_headers
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/{BOOKINGS_EXPORT}", headers=staff_headers
    )

    assert response.status_code == 200
    assert "Main hall" in response.text


async def test_staff_sees_company_of_booking_with_deleted_company(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)
    company_id = UUID(booking.json()["company_id"])
    await cancel_booking(client, company_headers, booking.json()["id"])
    await soft_delete_company(db_session, company_id)

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings", headers=staff_headers
    )

    assert response.status_code == 200
    assert [entry["company"]["name"] for entry in response.json()] == ["Acme AG"]


async def test_exports_still_render_industries_of_a_deleted_industry(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    industry = await client.post(
        "/api/industries", json={"name": "Robotics"}, headers=staff_headers
    )
    industry_id = industry.json()["id"]
    await complete_company_profile(company_headers, industry_ids=[industry_id])
    await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={"booth_zone_id": kp_setup.booth_zone_id, "confirm_profile": True},
        headers=company_headers,
    )
    deleted = await client.delete(
        f"/api/industries/{industry_id}", headers=staff_headers
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/{COMPANY_DETAILS_EXPORT}",
        headers=staff_headers,
    )

    assert deleted.status_code == 200
    assert response.status_code == 200
    assert "Robotics" in response.text


async def add_service_requirement(
    client: AsyncClient, staff_headers: dict[str, str], service_id: str
) -> Response:
    return await client.patch(
        f"/api/kp/services/{service_id}",
        json={
            "requirements": [
                {
                    "type": "file",
                    "name": "Logo",
                    "description": "Upload your company logo as a vector file.",
                }
            ]
        },
        headers=staff_headers,
    )


async def test_staff_sees_service_of_cancelled_booking_with_deleted_service(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)
    booking_id = booking.json()["id"]
    await cancel_booking(client, company_headers, booking_id)
    deleted = await client.delete(
        f"/api/kp/services/{kp_setup.service_id}", headers=staff_headers
    )

    listed = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings", headers=staff_headers
    )
    detail = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{booking_id}",
        headers=staff_headers,
    )

    assert deleted.status_code == 200
    assert listed.status_code == 200
    assert detail.status_code == 200
    assert [service["service"]["name"] for service in listed.json()[0]["services"]] == [
        "Electricity"
    ]
    assert [service["service"]["name"] for service in detail.json()["services"]] == [
        "Electricity"
    ]


async def test_exports_still_render_services_of_a_deleted_service(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    requirement = await add_service_requirement(
        client, staff_headers, kp_setup.service_id
    )
    booking = await register_booking(company_headers, kp_setup)
    await cancel_booking(client, company_headers, booking.json()["id"])
    await client.delete(
        f"/api/kp/services/{kp_setup.service_id}", headers=staff_headers
    )

    bookings_export = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/{BOOKINGS_EXPORT}", headers=staff_headers
    )
    requirements_export = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/{REQUIREMENTS_EXPORT}",
        headers=staff_headers,
    )

    assert requirement.status_code == 200
    assert bookings_export.status_code == 200
    assert "Electricity" in bookings_export.text
    assert requirements_export.status_code == 200
    assert "Logo" in requirements_export.text
