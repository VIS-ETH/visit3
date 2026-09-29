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
    offered_user, offered_headers = await company_headers_for(
        "beta", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    offered = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/offer",
        json={
            "company_id": str(offered_user.company_id),
            "booth_zone_id": gold.json()["id"],
            "deadline": (local_today() + timedelta(days=3)).isoformat(),
        },
        headers=staff_headers,
    )
    await client.post(
        f"/api/kp/bookings/{offered.json()['id']}/accept-offer",
        json={"confirm_profile": True, "accept_terms": True},
        headers=offered_headers,
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


def price_sum(bookings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        part: sum(booking["price"][part] for booking in bookings)
        for part in ("net", "vat", "gross")
    }


async def test_every_price_case_matches_the_booking_prices(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    event_url = f"/api/kp/events/{kp_setup.event_id}"
    gold = (
        await client.post(
            f"{event_url}/booth-zones",
            json={
                "name": "Gold",
                "color": "#AABBCC",
                "capacity": 1,
                "base_price": 30000,
                "included_services": [
                    {"service_id": kp_setup.service_id, "included_quantity": 1}
                ],
            },
            headers=staff_headers,
        )
    ).json()["id"]
    full = (
        await client.post(
            f"{event_url}/booth-zones",
            json={"name": "Full", "color": "#010203", "capacity": 0},
            headers=staff_headers,
        )
    ).json()["id"]

    async def register(name: str, zone_id: str, quantity: int) -> tuple[str, dict]:
        _, headers = await company_headers_for(
            name, create_user, auth_headers, csrf_headers, complete_company_profile
        )
        response = await client.post(
            f"{event_url}/bookings/register",
            json={
                "booth_zone_id": zone_id,
                "services": [{"service_id": kp_setup.service_id, "quantity": quantity}],
                "confirm_profile": True,
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text
        return response.json()["id"], headers

    included_id, _ = await register("included", gold, 2)
    added_id, added_headers = await register("added", kp_setup.booth_zone_id, 1)
    await client.post(f"/api/kp/bookings/{added_id}/accept", headers=staff_headers)
    added = await client.post(
        f"/api/kp/bookings/{added_id}/services",
        json={"services": [{"service_id": kp_setup.service_id, "quantity": 1}]},
        headers=added_headers,
    )
    assert added.status_code == 200, added.text
    waiting_id, waiting_headers = await register("waiting", kp_setup.booth_zone_id, 1)
    waitlisted = await client.put(
        f"/api/kp/bookings/{waiting_id}/upgrade-waitlist",
        json={"target_booth_zone_ids": [full]},
        headers=waiting_headers,
    )
    assert waitlisted.status_code == 200, waitlisted.text
    rejected_id, _ = await register("rejected", kp_setup.booth_zone_id, 1)
    await client.post(
        f"/api/kp/bookings/{rejected_id}/reject",
        json={"reason": "No space for this company"},
        headers=staff_headers,
    )
    await client.patch(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}",
        json={"base_price": 12500},
        headers=staff_headers,
    )

    bookings = (await client.get(f"{event_url}/bookings", headers=staff_headers)).json()
    by_id = {booking["id"]: booking for booking in bookings}
    active = [by_id[included_id], by_id[added_id], by_id[waiting_id]]
    details = [
        (
            await client.get(
                f"{event_url}/bookings/{booking['id']}", headers=staff_headers
            )
        ).json()
        for booking in active
    ]

    body = (await summary(client, staff_headers, kp_setup.event_id)).json()

    assert by_id[included_id]["net_total"] == 30000 + 5000
    assert by_id[added_id]["net_total"] == 12500 + 2 * 5000
    assert body["total"]["price"] == price_sum(active) == price_sum(details)
    assert body["total"]["count"] == 3
    assert body["total"]["base"] == 30000 + 2 * 12500
    assert body["total"]["services"] == 5000 + 2 * 5000 + 5000
    assert body["rejected_count"] == 1
    zones = {zone["name"]: zone for zone in body["by_zone"]}
    assert zones["Main hall"]["price"] == price_sum(
        [by_id[added_id], by_id[waiting_id]]
    )
    assert zones["Gold"]["price"] == by_id[included_id]["price"]
    assert zones["Full"]["count"] == 0


async def test_zone_rows_show_price_and_occupancy(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    register_booking: Callable[..., Awaitable[Response]],
):
    closed = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Closed", "color": "#010203", "capacity": 0, "base_price": 9900},
        headers=staff_headers,
    )
    _, first_headers = await company_headers_for(
        "first", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    await register_booking(first_headers, kp_setup)
    _, gone_headers = await company_headers_for(
        "gone", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    gone = (await register_booking(gone_headers, kp_setup)).json()
    await client.patch(
        f"/api/kp/bookings/{gone['id']}/status",
        json={"status": "CANCELLED"},
        headers=gone_headers,
    )
    offered_user, _ = await company_headers_for(
        "offered", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/offer",
        json={
            "company_id": str(offered_user.company_id),
            "booth_zone_id": closed.json()["id"],
            "deadline": (local_today() + timedelta(days=3)).isoformat(),
        },
        headers=staff_headers,
    )

    body = (await summary(client, staff_headers, kp_setup.event_id)).json()

    keys = ("base_price", "capacity", "count", "occupied", "free")
    zones = {zone["name"]: zone for zone in body["by_zone"]}
    assert {key: zones["Main hall"][key] for key in keys} == {
        "base_price": 10000,
        "capacity": 5,
        "count": 1,
        "occupied": 1,
        "free": 4,
    }
    assert {key: zones["Closed"][key] for key in keys} == {
        "base_price": 9900,
        "capacity": 0,
        "count": 0,
        "occupied": 1,
        "free": 0,
    }
    assert body["capacity"] == 5
    assert body["occupied"] == 2
    assert body["free"] == 4


async def test_a_pending_offer_is_listed_apart_from_the_booked_revenue(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    register_booking: Callable[..., Awaitable[Response]],
):
    _, booked_headers = await company_headers_for(
        "booked", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    booked = (await register_booking(booked_headers, kp_setup, quantity=1)).json()
    offered_user, _ = await company_headers_for(
        "pending", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    pending = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/offer",
        json={
            "company_id": str(offered_user.company_id),
            "booth_zone_id": kp_setup.booth_zone_id,
            "deadline": (local_today() + timedelta(days=3)).isoformat(),
        },
        headers=staff_headers,
    )
    bookings = {
        booking["id"]: booking
        for booking in (
            await client.get(
                f"/api/kp/events/{kp_setup.event_id}/bookings", headers=staff_headers
            )
        ).json()
    }

    body = (await summary(client, staff_headers, kp_setup.event_id)).json()

    assert body["total"]["count"] == 1
    assert body["total"]["price"] == bookings[booked["id"]]["price"]
    assert [entry["status"] for entry in body["by_status"]] == [
        "REGISTERED",
        "CONFIRMED",
    ]
    assert body["offered"]["count"] == 1
    assert body["offered"]["price"] == bookings[pending.json()["id"]]["price"]
    main_hall = body["by_zone"][0]
    assert main_hall["count"] == 1
    assert main_hall["occupied"] == 2
    assert main_hall["price"] == bookings[booked["id"]]["price"]
