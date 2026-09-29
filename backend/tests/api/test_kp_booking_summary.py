from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from httpx import AsyncClient, Response

from app.core.dates import local_today
from app.models.user import User
from tests.api.conftest import KpSetup


async def summary(
    client: AsyncClient, headers: dict[str, str], event_id: str
) -> Response:
    return await client.get(
        f"/api/kp/events/{event_id}/bookings/summary", headers=headers
    )


async def company_headers_for(
    name: str,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> tuple[User, dict[str, str]]:
    user = await create_user(
        email=f"{name}@example.com", password=None, company_name=f"{name} AG"
    )
    headers = {**await auth_headers(user), **csrf_headers}
    await complete_company_profile(headers)
    return user, headers


def zero_totals() -> dict[str, Any]:
    return {
        "count": 0,
        "base": 0,
        "services": 0,
        "price": {"net": 0, "vat": 0, "gross": 0},
    }


async def test_the_summary_adds_up_the_active_booking_prices(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    register_booking: Callable[..., Awaitable[Response]],
):
    gold = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Gold", "color": "#AABBCC", "capacity": 0, "base_price": 30000},
        headers=staff_headers,
    )
    _, registered_headers = await company_headers_for(
        "alpha", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    registered = (
        await register_booking(registered_headers, kp_setup, quantity=2)
    ).json()
    offered_user, _ = await company_headers_for(
        "beta", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    offered = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/offer",
        json={
            "company_id": str(offered_user.company_id),
            "booth_zone_id": gold.json()["id"],
            "cancel_until": (local_today() + timedelta(days=3)).isoformat(),
        },
        headers=staff_headers,
    )
    await client.post(
        f"/api/kp/bookings/{offered.json()['id']}/accept", headers=staff_headers
    )
    _, cancelled_headers = await company_headers_for(
        "gamma", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    cancelled = (await register_booking(cancelled_headers, kp_setup)).json()
    await client.patch(
        f"/api/kp/bookings/{cancelled['id']}/status",
        json={"status": "CANCELLED"},
        headers=cancelled_headers,
    )
    bookings = {
        booking["id"]: booking
        for booking in (
            await client.get(
                f"/api/kp/events/{kp_setup.event_id}/bookings", headers=staff_headers
            )
        ).json()
    }
    active = [bookings[registered["id"]], bookings[offered.json()["id"]]]
    zone_names = [
        zone["name"]
        for zone in (
            await client.get(
                f"/api/kp/events/{kp_setup.event_id}/booth-zones",
                headers=staff_headers,
            )
        ).json()
    ]

    response = await summary(client, staff_headers, kp_setup.event_id)

    assert response.status_code == 200
    body = response.json()
    assert body["total"]["count"] == 2
    assert body["total"]["price"] == {
        part: sum(booking["price"][part] for booking in active)
        for part in ("net", "vat", "gross")
    }
    assert body["total"]["base"] == 10000 + 30000
    assert body["total"]["services"] == body["total"]["price"]["net"] - 40000
    assert body["total"]["services"] == bookings[registered["id"]]["net_total"] - 10000
    assert {entry["status"]: entry["count"] for entry in body["by_status"]} == {
        "REGISTERED": 1,
        "CONFIRMED": 1,
    }
    confirmed = next(
        entry for entry in body["by_status"] if entry["status"] == "CONFIRMED"
    )
    assert confirmed["price"] == bookings[offered.json()["id"]]["price"]
    assert body["cancelled_count"] == 1
    assert body["rejected_count"] == 0
    assert [zone["name"] for zone in body["by_zone"]] == zone_names
    gold_totals = next(zone for zone in body["by_zone"] if zone["name"] == "Gold")
    assert gold_totals["count"] == 1
    assert gold_totals["base"] == 30000
    assert gold_totals["services"] == 0


async def test_an_event_without_bookings_sums_to_zero(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await summary(client, staff_headers, kp_setup.event_id)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == zero_totals()
    assert body["cancelled_count"] == 0
    assert [
        {key: zone[key] for key in ("count", "base", "services", "price")}
        for zone in body["by_zone"]
    ] == [zero_totals()]


async def test_an_unknown_event_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await summary(
        client, staff_headers, "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


async def test_companies_cannot_see_the_summary(
    client: AsyncClient, company_headers: dict[str, str], kp_setup: KpSetup
):
    response = await summary(client, company_headers, kp_setup.event_id)

    assert response.status_code == 403
