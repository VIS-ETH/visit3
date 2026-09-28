from collections.abc import Awaitable, Callable
from uuid import UUID

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kp_event import KpEventBoothZoneServiceLink
from tests.api.conftest import KpSetup

ZONE_PRICE = 10000
SERVICE_PRICE = 5000


async def include_service_in_zone(
    db_session: AsyncSession, kp_setup: KpSetup, included_quantity: int
) -> None:
    db_session.add(
        KpEventBoothZoneServiceLink(
            booth_zone_id=UUID(kp_setup.booth_zone_id),
            service_id=UUID(kp_setup.service_id),
            included_quantity=included_quantity,
        )
    )
    await db_session.commit()


async def test_booking_price_breakdown_uses_the_default_vat_rate(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    response = await register_booking(company_headers, kp_setup)

    assert response.status_code == 200
    body = response.json()
    assert body["net_total"] == ZONE_PRICE + SERVICE_PRICE
    assert body["price"] == {"net": 15000, "vat": 1215, "gross": 16215}


async def test_service_line_items_expose_charged_quantity_and_net(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    db_session: AsyncSession,
    register_booking: Callable[..., Awaitable[Response]],
):
    await include_service_in_zone(db_session, kp_setup, included_quantity=1)

    response = await register_booking(company_headers, kp_setup, quantity=2)

    assert response.status_code == 200
    body = response.json()
    assert [
        (
            service["quantity"],
            service["included_quantity"],
            service["charged_quantity"],
            service["unit_price"],
            service["line_net"],
        )
        for service in body["services"]
    ] == [(2, 1, 1, SERVICE_PRICE, SERVICE_PRICE)]
    assert [charge["line_net"] for charge in body["additional_service_charges"]] == [
        SERVICE_PRICE
    ]


async def test_included_services_are_not_charged(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    db_session: AsyncSession,
    register_booking: Callable[..., Awaitable[Response]],
):
    await include_service_in_zone(db_session, kp_setup, included_quantity=2)

    response = await register_booking(company_headers, kp_setup, quantity=1)

    assert response.status_code == 200
    body = response.json()
    assert [service["line_net"] for service in body["services"]] == [0]
    assert body["net_total"] == ZONE_PRICE
    assert body["price"] == {"net": 10000, "vat": 810, "gross": 10810}


async def test_staff_booking_response_carries_the_breakdown(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings", headers=staff_headers
    )

    assert response.status_code == 200
    assert [booking["price"] for booking in response.json()] == [
        {"net": 15000, "vat": 1215, "gross": 16215}
    ]


async def test_price_breakdown_follows_the_event_vat_rate(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await client.patch(
        f"/api/kp/events/{kp_setup.event_id}",
        json={"vat_rate_percent": 2.6},
        headers=staff_headers,
    )

    await register_booking(company_headers, kp_setup)
    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/my-booking", headers=company_headers
    )

    assert response.status_code == 200
    assert response.json()["price"] == {"net": 15000, "vat": 390, "gross": 15390}
