from collections.abc import Awaitable, Callable
from datetime import timedelta

import pytest
from httpx import AsyncClient, Response

from app.core.dates import local_today
from app.models.user import User
from tests.api.conftest import KpSetup


async def test_an_offer_into_a_full_zone_is_refused(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    company_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
    create_user: Callable[..., Awaitable[User]],
):
    zone = await client.patch(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}",
        json={"capacity": 1},
        headers=president_headers,
    )
    assert zone.status_code == 200, zone.text
    assert (await register_booking(company_headers, kp_setup)).status_code == 200
    late = await create_user(email="late@example.com", company_name="Late AG")

    offered = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/offer",
        json={
            "company_id": str(late.company_id),
            "booth_zone_id": kp_setup.booth_zone_id,
            "deadline": (local_today() + timedelta(days=3)).isoformat(),
        },
        headers=president_headers,
    )

    assert offered.status_code == 409, offered.text


async def test_a_refused_staff_edit_changes_nothing(
    client: AsyncClient,
    kp_setup: KpSetup,
    staff_headers: dict[str, str],
    president_headers: dict[str, str],
    company_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = (await register_booking(company_headers, kp_setup)).json()
    side = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Side", "color": "#ABCDEF", "capacity": 3},
        headers=president_headers,
    )

    refused = await client.patch(
        f"/api/kp/bookings/{booking['id']}",
        json={
            "booth_zone_id": side.json()["id"],
            "services": [{"service_id": kp_setup.service_id, "quantity": 99}],
        },
        headers=staff_headers,
    )

    assert refused.status_code == 400, refused.text
    after = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{booking['id']}",
        headers=staff_headers,
    )
    assert after.json()["booth_zone_id"] == kp_setup.booth_zone_id
    assert [service["quantity"] for service in after.json()["services"]] == [1]


async def test_staff_can_remove_a_deactivated_service_from_a_booking(
    client: AsyncClient,
    kp_setup: KpSetup,
    staff_headers: dict[str, str],
    president_headers: dict[str, str],
    company_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = (await register_booking(company_headers, kp_setup)).json()
    deactivated = await client.patch(
        f"/api/kp/services/{kp_setup.service_id}",
        json={"is_active": False},
        headers=president_headers,
    )
    assert deactivated.status_code == 200, deactivated.text

    removed = await client.patch(
        f"/api/kp/bookings/{booking['id']}",
        json={"services": [{"service_id": kp_setup.service_id, "quantity": 0}]},
        headers=staff_headers,
    )

    assert removed.status_code == 200, removed.text
    assert removed.json()["services"] == []


@pytest.mark.parametrize("days", [366, 1_000_000])
async def test_a_reminder_offset_beyond_a_year_is_rejected(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    days: int,
):
    response = await client.patch(
        f"/api/kp/events/{kp_setup.event_id}",
        json={"finalization_reminder_days": days},
        headers=president_headers,
    )

    assert response.status_code == 422, response.text


async def test_prices_and_capacities_beyond_the_database_range_are_rejected(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
):
    service = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={"name": "Gold plated", "price": 2**31},
        headers=president_headers,
    )
    zone = await client.patch(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}",
        json={"capacity": 2**31},
        headers=president_headers,
    )

    assert service.status_code == 422, service.text
    assert zone.status_code == 422, zone.text
