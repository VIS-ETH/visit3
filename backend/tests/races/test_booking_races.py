import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.services.waitlist_promotion as waitlist_promotion
from app.core.dates import local_today
from app.models.user import User
from app.repositories.kp_repository import KpRepository
from app.services.booking_notifier import SilentBookingNotifier
from app.services.booking_offers import process_booking_offers
from tests.api.conftest import KpSetup

Sessions = async_sessionmaker[AsyncSession]
SlowDown = Callable[..., None]


@dataclass(frozen=True)
class World:
    gold: str
    silver: str
    headers: dict[str, dict[str, str]]
    bookings: dict[str, str]


async def scalar(sessions: Sessions, sql: str, **params: Any) -> Any:
    async with sessions() as session:
        return (await session.execute(text(sql), params)).scalar_one()


async def active_in_zone(sessions: Sessions, zone_id: str) -> int:
    return await scalar(
        sessions,
        "SELECT count(*) FROM kpeventbooking WHERE booth_zone_id = :zone "
        "AND status NOT IN ('CANCELLED', 'REJECTED', 'EXPIRED') "
        "AND deleted_at IS NULL",
        zone=zone_id,
    )


async def make_zone(
    client: AsyncClient,
    president_headers: dict[str, str],
    event_id: str,
    name: str,
    color: str,
    capacity: int,
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": name, "color": color, "capacity": capacity},
        headers=president_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def make_service(
    client: AsyncClient, president_headers: dict[str, str], event_id: str, **fields: Any
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/services",
        json={"name": "Wifi", "price": 100, **fields},
        headers=president_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def register(
    client: AsyncClient, headers: dict[str, str], event_id: str, zone_id: str
) -> Response:
    return await client.post(
        f"/api/kp/events/{event_id}/bookings/register",
        json={"booth_zone_id": zone_id, "confirm_profile": True},
        headers=headers,
    )


async def wait_for(
    client: AsyncClient, headers: dict[str, str], booking_id: str, zone_id: str
) -> None:
    response = await client.put(
        f"/api/kp/bookings/{booking_id}/upgrade-waitlist",
        json={"target_booth_zone_ids": [zone_id]},
        headers=headers,
    )
    assert response.status_code == 200, response.text


async def cancel(
    client: AsyncClient, headers: dict[str, str], booking_id: str
) -> Response:
    return await client.patch(
        f"/api/kp/bookings/{booking_id}/status",
        json={"status": "CANCELLED"},
        headers=headers,
    )


async def add_services(
    client: AsyncClient,
    headers: dict[str, str],
    booking_id: str,
    service_id: str,
    quantity: int,
) -> Response:
    return await client.post(
        f"/api/kp/bookings/{booking_id}/services",
        json={"services": [{"service_id": service_id, "quantity": quantity}]},
        headers=headers,
    )


async def later(seconds: float, request: Awaitable[Response]) -> Response:
    await asyncio.sleep(seconds)
    return await request


def slow_locks(slow_down: SlowDown, seconds: float) -> None:
    slow_down(KpRepository, "lock_model_by_id", seconds, before=True)
    slow_down(KpRepository, "lock_booth_zone", seconds, before=True)


@pytest.fixture
async def world(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> World:
    event = kp_setup.event_id
    gold = await make_zone(client, president_headers, event, "Gold", "#AA0000", 1)
    silver = await make_zone(client, president_headers, event, "Silver", "#00AA00", 10)
    headers: dict[str, dict[str, str]] = {}
    for name in ("alpha", "beta", "gamma", "delta"):
        user = await create_user(
            email=f"{name}@example.com", password=None, company_name=f"{name} AG"
        )
        headers[name] = {**await auth_headers(user), **csrf_headers}
        await complete_company_profile(headers[name])
    bookings: dict[str, str] = {}
    for name, zone in (("alpha", gold), ("beta", silver), ("gamma", silver)):
        response = await register(client, headers[name], event, zone)
        assert response.status_code == 200, response.text
        bookings[name] = response.json()["id"]
    return World(gold, silver, headers, bookings)


async def test_parallel_additions_of_a_service_are_all_counted(
    client: AsyncClient,
    kp_setup: KpSetup,
    company_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
    pg_sessionmaker: Sessions,
    slow_down: SlowDown,
):
    booking = (await register_booking(company_headers, kp_setup, quantity=1)).json()
    slow_locks(slow_down, 0.3)

    responses = await asyncio.gather(
        *[
            add_services(client, company_headers, booking["id"], kp_setup.service_id, 1)
            for _ in range(2)
        ]
    )

    added = [response.status_code for response in responses].count(200)
    quantity = await scalar(
        pg_sessionmaker,
        "SELECT coalesce(sum(quantity), 0) FROM kpeventbookingservice "
        "WHERE booking_id = :booking AND deleted_at IS NULL",
        booking=booking["id"],
    )
    assert quantity == 1 + added


async def test_parallel_additions_cannot_exceed_the_per_booking_maximum(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    company_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
    pg_sessionmaker: Sessions,
    slow_down: SlowDown,
):
    booking = (await register_booking(company_headers, kp_setup, quantity=1)).json()
    wifi = await make_service(
        client, president_headers, kp_setup.event_id, max_quantity_per_booking=2
    )
    slow_locks(slow_down, 0.3)

    await asyncio.gather(
        *[
            add_services(client, company_headers, booking["id"], wifi, 2)
            for _ in range(2)
        ]
    )

    quantity = await scalar(
        pg_sessionmaker,
        "SELECT sum(quantity) FROM kpeventbookingservice "
        "WHERE booking_id = :booking AND service_id = :service",
        booking=booking["id"],
        service=wifi,
    )
    assert quantity <= 2


async def test_a_promotion_and_a_staff_move_cannot_overfill_a_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    world: World,
    pg_sessionmaker: Sessions,
    slow_down: SlowDown,
):
    await wait_for(client, world.headers["beta"], world.bookings["beta"], world.gold)
    slow_down(KpRepository, "count_active_bookings_for_zone", 0.3)

    await asyncio.gather(
        cancel(client, world.headers["alpha"], world.bookings["alpha"]),
        later(
            0.1,
            client.patch(
                f"/api/kp/bookings/{world.bookings['gamma']}",
                json={"booth_zone_id": world.gold},
                headers=staff_headers,
            ),
        ),
    )

    assert await active_in_zone(pg_sessionmaker, world.gold) <= 1


async def test_a_registration_cannot_slip_into_a_zone_during_a_promotion(
    client: AsyncClient,
    kp_setup: KpSetup,
    world: World,
    pg_sessionmaker: Sessions,
    slow_down: SlowDown,
):
    await wait_for(client, world.headers["beta"], world.bookings["beta"], world.gold)
    await wait_for(client, world.headers["gamma"], world.bookings["gamma"], world.gold)
    cancelled = await cancel(client, world.headers["beta"], world.bookings["beta"])
    assert cancelled.status_code == 200, cancelled.text
    slow_down(KpRepository, "count_active_bookings_for_zone", 0.3)

    await asyncio.gather(
        cancel(client, world.headers["alpha"], world.bookings["alpha"]),
        later(
            0.35,
            register(client, world.headers["delta"], kp_setup.event_id, world.gold),
        ),
    )

    assert await active_in_zone(pg_sessionmaker, world.gold) <= 1


async def test_a_promotion_and_a_zone_switch_do_not_deadlock(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    world: World,
    slow_down: SlowDown,
):
    bronze = await make_zone(
        client, president_headers, kp_setup.event_id, "Bronze", "#0000AA", 10
    )
    await wait_for(client, world.headers["beta"], world.bookings["beta"], world.gold)
    slow_down(KpRepository, "count_active_bookings_for_zone", 0.4)
    slow_locks(slow_down, 0.2)

    cancelled, switched = await asyncio.gather(
        cancel(client, world.headers["alpha"], world.bookings["alpha"]),
        later(
            0.05,
            client.post(
                f"/api/kp/bookings/{world.bookings['beta']}/switch-zone",
                json={"booth_zone_id": bronze},
                headers=world.headers["beta"],
            ),
        ),
    )

    assert cancelled.status_code < 500, cancelled.text
    assert switched.status_code < 500, switched.text


async def test_a_zone_deleted_during_a_registration_holds_no_booking(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    pg_sessionmaker: Sessions,
    slow_down: SlowDown,
):
    await complete_company_profile(company_headers)
    slow_down(KpRepository, "count_active_bookings_for_zone", 0.4)

    await asyncio.gather(
        client.delete(
            f"/api/kp/booth-zones/{kp_setup.booth_zone_id}", headers=president_headers
        ),
        later(
            0.1,
            register(
                client, company_headers, kp_setup.event_id, kp_setup.booth_zone_id
            ),
        ),
    )

    deleted = await scalar(
        pg_sessionmaker,
        "SELECT deleted_at IS NOT NULL FROM kpeventboothzone WHERE id = :zone",
        zone=kp_setup.booth_zone_id,
    )
    taken = await active_in_zone(pg_sessionmaker, kp_setup.booth_zone_id)
    assert not (deleted and taken)


async def test_a_service_deleted_during_an_addition_is_not_booked(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    company_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
    pg_sessionmaker: Sessions,
    slow_down: SlowDown,
):
    booking = (await register_booking(company_headers, kp_setup)).json()
    wifi = await make_service(client, president_headers, kp_setup.event_id)
    slow_down(KpRepository, "count_active_bookings_with_service", 0.4)

    await asyncio.gather(
        client.delete(f"/api/kp/services/{wifi}", headers=president_headers),
        later(0.1, add_services(client, company_headers, booking["id"], wifi, 1)),
    )

    deleted = await scalar(
        pg_sessionmaker,
        "SELECT deleted_at IS NOT NULL FROM kpeventservice WHERE id = :service",
        service=wifi,
    )
    mine = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/my-booking", headers=company_headers
    )
    names = [service["service"]["name"] for service in mine.json()["services"]]
    assert not (deleted and "Wifi" in names)


async def test_an_addition_during_a_confirmation_is_flagged(
    client: AsyncClient,
    kp_setup: KpSetup,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
    slow_down: SlowDown,
):
    booking = (await register_booking(company_headers, kp_setup)).json()
    slow_locks(slow_down, 0.4)

    await asyncio.gather(
        add_services(client, company_headers, booking["id"], kp_setup.service_id, 1),
        later(
            0.1,
            client.post(
                f"/api/kp/bookings/{booking['id']}/accept", headers=staff_headers
            ),
        ),
    )

    detail = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{booking['id']}",
        headers=staff_headers,
    )
    body = detail.json()
    assert not (
        body["status"] == "CONFIRMED"
        and body["services"][0]["quantity"] == 2
        and body["added_after_confirmation"] == []
    )


async def test_parallel_edits_cannot_exceed_the_total_stock(
    client: AsyncClient,
    kp_setup: KpSetup,
    staff_headers: dict[str, str],
    president_headers: dict[str, str],
    world: World,
    pg_sessionmaker: Sessions,
    slow_down: SlowDown,
):
    limited = await make_service(
        client,
        president_headers,
        kp_setup.event_id,
        max_quantity_per_booking=5,
        max_total_quantity=2,
    )
    slow_down(KpRepository, "count_active_charged_service_quantity", 0.3)

    await asyncio.gather(
        client.patch(
            f"/api/kp/bookings/{world.bookings['beta']}",
            json={"services": [{"service_id": limited, "quantity": 2}]},
            headers=staff_headers,
        ),
        add_services(
            client, world.headers["gamma"], world.bookings["gamma"], limited, 2
        ),
    )

    total = await scalar(
        pg_sessionmaker,
        "SELECT coalesce(sum(quantity), 0) FROM kpeventbookingservice "
        "WHERE service_id = :service",
        service=limited,
    )
    assert total <= 2


async def test_an_offer_extended_during_the_expiry_job_stays_open(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    world: World,
    create_user: Callable[..., Awaitable[User]],
    pg_sessionmaker: Sessions,
    slow_down: SlowDown,
):
    late = await create_user(
        email="late@example.com", password=None, company_name="Late AG"
    )
    offered = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/offer",
        json={
            "company_id": str(late.company_id),
            "booth_zone_id": world.silver,
            "deadline": local_today().isoformat(),
        },
        headers=president_headers,
    )
    assert offered.status_code == 200, offered.text
    offer_id = offered.json()["id"]
    async with pg_sessionmaker() as session:
        await session.execute(
            text("UPDATE kpeventbooking SET offer_deadline = :day WHERE id = :offer"),
            {"day": local_today() - timedelta(days=1), "offer": offer_id},
        )
        await session.commit()
    slow_down(KpRepository, "list_pending_offers", 0.4)

    async def expire() -> None:
        async with pg_sessionmaker() as session:
            await process_booking_offers(
                KpRepository(session),
                SilentBookingNotifier(),
                datetime.now(timezone.utc),
            )

    _, extended = await asyncio.gather(
        expire(),
        later(
            0.1,
            client.patch(
                f"/api/kp/bookings/{offer_id}/offer",
                json={"deadline": (local_today() + timedelta(days=5)).isoformat()},
                headers=president_headers,
            ),
        ),
    )

    status = await scalar(
        pg_sessionmaker,
        "SELECT status FROM kpeventbooking WHERE id = :offer",
        offer=offer_id,
    )
    assert not (extended.status_code == 200 and status == "EXPIRED")


async def test_a_registration_waiting_for_the_zone_lock_sees_the_closed_zone(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    slow_down: SlowDown,
):
    await complete_company_profile(company_headers)
    slow_locks(slow_down, 0.5)

    registered, closed = await asyncio.gather(
        register(client, company_headers, kp_setup.event_id, kp_setup.booth_zone_id),
        later(
            0.7,
            client.patch(
                f"/api/kp/booth-zones/{kp_setup.booth_zone_id}",
                json={"registration_open": False, "capacity": 0},
                headers=president_headers,
            ),
        ),
    )

    assert closed.status_code == 200, closed.text
    assert registered.status_code != 200


async def test_a_promotion_leaves_a_booking_confirmed_meanwhile_in_its_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    world: World,
    pg_sessionmaker: Sessions,
    slow_down: SlowDown,
):
    await wait_for(client, world.headers["beta"], world.bookings["beta"], world.gold)
    slow_down(waitlist_promotion, "service_exceeding_stock", 0.4)

    _, confirmed = await asyncio.gather(
        cancel(client, world.headers["alpha"], world.bookings["alpha"]),
        later(
            0.2,
            client.post(
                f"/api/kp/bookings/{world.bookings['beta']}/accept",
                headers=staff_headers,
            ),
        ),
    )

    async with pg_sessionmaker() as session:
        status, zone = (
            await session.execute(
                text("SELECT status, booth_zone_id FROM kpeventbooking WHERE id = :b"),
                {"b": world.bookings["beta"]},
            )
        ).one()
    assert not (
        status == "CONFIRMED"
        and str(zone) == world.gold
        and confirmed.json()["booth_zone_id"] == world.silver
    )
