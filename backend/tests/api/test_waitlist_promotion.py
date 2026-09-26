from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from unittest.mock import AsyncMock
from uuid import UUID

import grpc
import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kp_event import KpEventBoothZoneServiceLink
from app.models.user import User
from tests.api.conftest import KpSetup, decoded_subject, move_event_into_the_past

PROMOTION_SUBJECT = (
    "VISIT: Platz in Gold frei geworden / VISIT: A spot in Gold became available"
)
REJECTION_REASON = "The booth zone is no longer available for this company."


@dataclass(frozen=True)
class WaitlistWorld:
    event_id: str
    home_zone_id: str
    upgrade_zone_id: str
    spare_zone_id: str
    holder_booking_id: str
    first_booking_id: str
    second_booking_id: str
    holder_headers: dict[str, str]
    first_headers: dict[str, str]
    second_headers: dict[str, str]
    staff_headers: dict[str, str]


@pytest.fixture
def company_headers_factory(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> Callable[[str], Awaitable[dict[str, str]]]:
    async def _company_headers(name: str) -> dict[str, str]:
        user = await create_user(
            email=f"{name}@example.com", password=None, company_name=f"{name} AG"
        )
        return {**await auth_headers(user), **csrf_headers}

    return _company_headers


async def create_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    event_id: str,
    *,
    name: str,
    color: str,
    capacity: int,
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": name, "color": color, "capacity": capacity},
        headers=staff_headers,
    )
    return response.json()["id"]


async def register_into(
    client: AsyncClient,
    complete_company_profile: Callable[..., Awaitable[Response]],
    headers: dict[str, str],
    event_id: str,
    booth_zone_id: str,
) -> str:
    await complete_company_profile(headers)
    response = await client.post(
        f"/api/kp/events/{event_id}/bookings/register",
        json={"booth_zone_id": booth_zone_id, "confirm_profile": True},
        headers=headers,
    )
    return response.json()["id"]


async def join_waitlist(
    client: AsyncClient,
    headers: dict[str, str],
    booking_id: str,
    target_booth_zone_ids: list[str],
) -> Response:
    return await client.put(
        f"/api/kp/bookings/{booking_id}/upgrade-waitlist",
        json={"target_booth_zone_ids": target_booth_zone_ids},
        headers=headers,
    )


async def booth_zone_of(
    client: AsyncClient, world: WaitlistWorld, booking_id: str
) -> str:
    response = await client.get(
        f"/api/kp/events/{world.event_id}/bookings/{booking_id}",
        headers=world.staff_headers,
    )
    return response.json()["booth_zone_id"]


@pytest.fixture
async def waitlist_world(
    client: AsyncClient,
    kp_setup: KpSetup,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    company_headers_factory: Callable[[str], Awaitable[dict[str, str]]],
) -> WaitlistWorld:
    upgrade_zone_id = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        name="Gold",
        color="#AABBCC",
        capacity=1,
    )
    spare_zone_id = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        name="Silver",
        color="#CCBBAA",
        capacity=0,
    )
    first_headers = await company_headers_factory("first")
    second_headers = await company_headers_factory("second")

    holder_booking_id = await register_into(
        client,
        complete_company_profile,
        company_headers,
        kp_setup.event_id,
        upgrade_zone_id,
    )
    first_booking_id = await register_into(
        client,
        complete_company_profile,
        first_headers,
        kp_setup.event_id,
        kp_setup.booth_zone_id,
    )
    second_booking_id = await register_into(
        client,
        complete_company_profile,
        second_headers,
        kp_setup.event_id,
        kp_setup.booth_zone_id,
    )
    await join_waitlist(client, first_headers, first_booking_id, [upgrade_zone_id])
    await join_waitlist(client, second_headers, second_booking_id, [upgrade_zone_id])

    return WaitlistWorld(
        event_id=kp_setup.event_id,
        home_zone_id=kp_setup.booth_zone_id,
        upgrade_zone_id=upgrade_zone_id,
        spare_zone_id=spare_zone_id,
        holder_booking_id=holder_booking_id,
        first_booking_id=first_booking_id,
        second_booking_id=second_booking_id,
        holder_headers=company_headers,
        first_headers=first_headers,
        second_headers=second_headers,
        staff_headers=staff_headers,
    )


async def cancel_holder(client: AsyncClient, world: WaitlistWorld) -> Response:
    return await client.patch(
        f"/api/kp/bookings/{world.holder_booking_id}/status",
        json={"status": "CANCELLED"},
        headers=world.holder_headers,
    )


async def reject_holder(client: AsyncClient, world: WaitlistWorld) -> Response:
    return await client.post(
        f"/api/kp/bookings/{world.holder_booking_id}/reject",
        json={"reason": REJECTION_REASON},
        headers=world.staff_headers,
    )


async def delete_holder(client: AsyncClient, world: WaitlistWorld) -> Response:
    return await client.delete(
        f"/api/kp/bookings/{world.holder_booking_id}",
        headers=world.staff_headers,
    )


async def move_holder_away(client: AsyncClient, world: WaitlistWorld) -> Response:
    return await client.patch(
        f"/api/kp/bookings/{world.holder_booking_id}",
        json={"booth_zone_id": world.home_zone_id},
        headers=world.staff_headers,
    )


async def switch_holder_away(client: AsyncClient, world: WaitlistWorld) -> Response:
    return await client.post(
        f"/api/kp/bookings/{world.holder_booking_id}/switch-zone",
        json={"booth_zone_id": world.home_zone_id},
        headers=world.holder_headers,
    )


async def grow_capacity(client: AsyncClient, world: WaitlistWorld) -> Response:
    return await client.patch(
        f"/api/kp/booth-zones/{world.upgrade_zone_id}",
        json={"capacity": 2},
        headers=world.staff_headers,
    )


FREEING_PATHS: dict[
    str, Callable[[AsyncClient, WaitlistWorld], Awaitable[Response]]
] = {
    "company-cancel": cancel_holder,
    "company-switch": switch_holder_away,
    "staff-reject": reject_holder,
    "staff-delete": delete_holder,
    "staff-zone-change": move_holder_away,
    "zone-capacity-increase": grow_capacity,
}


@pytest.mark.parametrize("path", sorted(FREEING_PATHS))
async def test_every_freeing_path_promotes_the_first_waitlisted_booking(
    client: AsyncClient, waitlist_world: WaitlistWorld, path: str
):
    response = await FREEING_PATHS[path](client, waitlist_world)

    assert response.status_code == 200
    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.first_booking_id)
        == waitlist_world.upgrade_zone_id
    )
    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.second_booking_id)
        == waitlist_world.home_zone_id
    )


async def test_promotion_clears_the_waitlist_of_the_promoted_booking(
    client: AsyncClient, waitlist_world: WaitlistWorld
):
    await join_waitlist(
        client,
        waitlist_world.first_headers,
        waitlist_world.first_booking_id,
        [waitlist_world.upgrade_zone_id, waitlist_world.spare_zone_id],
    )

    await cancel_holder(client, waitlist_world)

    remaining = await client.get(
        f"/api/kp/bookings/{waitlist_world.first_booking_id}/upgrade-waitlist",
        headers=waitlist_world.first_headers,
    )
    assert remaining.json() == []


async def test_promotion_keeps_the_booking_registered_and_clears_the_booth_number(
    client: AsyncClient, waitlist_world: WaitlistWorld
):
    await client.patch(
        f"/api/kp/bookings/{waitlist_world.first_booking_id}/booth-number",
        json={"booth_nr": 3},
        headers=waitlist_world.staff_headers,
    )

    await cancel_holder(client, waitlist_world)

    promoted = await client.get(
        f"/api/kp/events/{waitlist_world.event_id}/bookings/{waitlist_world.first_booking_id}",
        headers=waitlist_world.staff_headers,
    )
    assert promoted.json()["status"] == "REGISTERED"
    assert promoted.json()["booth_nr"] is None


async def test_the_lowest_priority_rank_is_promoted_first(
    client: AsyncClient, waitlist_world: WaitlistWorld
):
    await join_waitlist(
        client,
        waitlist_world.first_headers,
        waitlist_world.first_booking_id,
        [waitlist_world.spare_zone_id, waitlist_world.upgrade_zone_id],
    )

    await cancel_holder(client, waitlist_world)

    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.second_booking_id)
        == waitlist_world.upgrade_zone_id
    )
    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.first_booking_id)
        == waitlist_world.home_zone_id
    )


async def test_a_confirmed_booking_keeps_its_zone_when_a_spot_frees_up(
    client: AsyncClient, waitlist_world: WaitlistWorld
):
    await client.post(
        f"/api/kp/bookings/{waitlist_world.first_booking_id}/accept",
        headers=waitlist_world.staff_headers,
    )

    await cancel_holder(client, waitlist_world)

    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.first_booking_id)
        == waitlist_world.home_zone_id
    )
    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.second_booking_id)
        == waitlist_world.upgrade_zone_id
    )


async def test_waitlist_entries_of_cancelled_bookings_are_skipped_and_dropped(
    client: AsyncClient, waitlist_world: WaitlistWorld
):
    await client.patch(
        f"/api/kp/bookings/{waitlist_world.first_booking_id}/status",
        json={"status": "CANCELLED"},
        headers=waitlist_world.first_headers,
    )

    await cancel_holder(client, waitlist_world)

    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.second_booking_id)
        == waitlist_world.upgrade_zone_id
    )
    dropped = await client.get(
        f"/api/kp/bookings/{waitlist_world.first_booking_id}/upgrade-waitlist",
        headers=waitlist_world.first_headers,
    )
    assert dropped.json() == []


async def test_promotion_stops_once_the_zone_is_full_again(
    client: AsyncClient, waitlist_world: WaitlistWorld
):
    await cancel_holder(client, waitlist_world)

    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.second_booking_id)
        == waitlist_world.home_zone_id
    )


async def test_two_free_spots_promote_two_bookings(
    client: AsyncClient, waitlist_world: WaitlistWorld
):
    response = await client.patch(
        f"/api/kp/booth-zones/{waitlist_world.upgrade_zone_id}",
        json={"capacity": 3},
        headers=waitlist_world.staff_headers,
    )

    assert response.status_code == 200
    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.first_booking_id)
        == waitlist_world.upgrade_zone_id
    )
    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.second_booking_id)
        == waitlist_world.upgrade_zone_id
    )


async def test_promotion_stops_after_the_finalization_deadline(
    client: AsyncClient, db_session, waitlist_world: WaitlistWorld
):
    await move_event_into_the_past(db_session, waitlist_world.event_id)

    await cancel_holder(client, waitlist_world)

    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.first_booking_id)
        == waitlist_world.home_zone_id
    )
    waiting = await client.get(
        f"/api/kp/bookings/{waitlist_world.first_booking_id}/upgrade-waitlist",
        headers=waitlist_world.first_headers,
    )
    assert [entry["target_booth_zone_id"] for entry in waiting.json()] == [
        waitlist_world.upgrade_zone_id
    ]


@dataclass(frozen=True)
class StockWorld:
    event_id: str
    home_zone_id: str
    upgrade_zone_id: str
    service_id: str
    waiting_booking_id: str
    waiting_headers: dict[str, str]
    staff_headers: dict[str, str]


@pytest.fixture
async def stock_world(
    client: AsyncClient,
    db_session: AsyncSession,
    kp_setup: KpSetup,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    company_headers_factory: Callable[[str], Awaitable[dict[str, str]]],
) -> StockWorld:
    db_session.add(
        KpEventBoothZoneServiceLink(
            booth_zone_id=UUID(kp_setup.booth_zone_id),
            service_id=UUID(kp_setup.service_id),
            included_quantity=1,
        )
    )
    await db_session.commit()
    db_session.expunge_all()
    upgrade_zone_id = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        name="Gold",
        color="#AABBCC",
        capacity=1,
    )
    holder_booking_id = await register_into(
        client,
        complete_company_profile,
        company_headers,
        kp_setup.event_id,
        upgrade_zone_id,
    )
    await client.post(
        f"/api/kp/bookings/{holder_booking_id}/services",
        json={"services": [{"service_id": kp_setup.service_id, "quantity": 1}]},
        headers=company_headers,
    )
    waiting_headers = await company_headers_factory("waiting")
    waiting_booking_id = await register_into(
        client,
        complete_company_profile,
        waiting_headers,
        kp_setup.event_id,
        kp_setup.booth_zone_id,
    )
    await join_waitlist(client, waiting_headers, waiting_booking_id, [upgrade_zone_id])
    return StockWorld(
        event_id=kp_setup.event_id,
        home_zone_id=kp_setup.booth_zone_id,
        upgrade_zone_id=upgrade_zone_id,
        service_id=kp_setup.service_id,
        waiting_booking_id=waiting_booking_id,
        waiting_headers=waiting_headers,
        staff_headers=staff_headers,
    )


async def limit_service_stock(
    client: AsyncClient, world: StockWorld, max_total_quantity: int
) -> Response:
    return await client.patch(
        f"/api/kp/services/{world.service_id}",
        json={"max_total_quantity": max_total_quantity},
        headers=world.staff_headers,
    )


async def free_upgrade_spot(client: AsyncClient, world: StockWorld) -> Response:
    return await client.patch(
        f"/api/kp/booth-zones/{world.upgrade_zone_id}",
        json={"capacity": 2},
        headers=world.staff_headers,
    )


async def waiting_booking_zone(client: AsyncClient, world: StockWorld) -> str:
    response = await client.get(
        f"/api/kp/events/{world.event_id}/bookings/{world.waiting_booking_id}",
        headers=world.staff_headers,
    )
    return response.json()["booth_zone_id"]


async def test_promotion_skips_a_booking_that_would_exceed_the_service_stock(
    client: AsyncClient, stock_world: StockWorld
):
    await limit_service_stock(client, stock_world, 1)

    response = await free_upgrade_spot(client, stock_world)

    assert response.status_code == 200
    assert await waiting_booking_zone(client, stock_world) == stock_world.home_zone_id
    waiting = await client.get(
        f"/api/kp/bookings/{stock_world.waiting_booking_id}/upgrade-waitlist",
        headers=stock_world.waiting_headers,
    )
    assert [entry["target_booth_zone_id"] for entry in waiting.json()] == [
        stock_world.upgrade_zone_id
    ]


async def test_promotion_proceeds_while_the_stock_covers_the_new_charge(
    client: AsyncClient, stock_world: StockWorld
):
    await limit_service_stock(client, stock_world, 2)

    response = await free_upgrade_spot(client, stock_world)

    assert response.status_code == 200
    assert (
        await waiting_booking_zone(client, stock_world) == stock_world.upgrade_zone_id
    )


async def test_each_promotion_mails_the_promoted_company_once(
    client: AsyncClient, waitlist_world: WaitlistWorld, mail_stub: AsyncMock
):
    mail_stub.SendMail.reset_mock()

    await cancel_holder(client, waitlist_world)

    subjects = [
        decoded_subject(call.args[0]) for call in mail_stub.SendMail.await_args_list
    ]
    assert subjects == [PROMOTION_SUBJECT]
    recipients = [
        address.mail_address.address
        for address in mail_stub.SendMail.await_args.args[0].to
    ]
    assert recipients == ["first@example.com"]


async def test_rejection_promotes_even_when_the_mail_service_fails(
    client: AsyncClient, waitlist_world: WaitlistWorld, mail_stub: AsyncMock
):
    mail_stub.SendMail.side_effect = grpc.RpcError()

    response = await reject_holder(client, waitlist_world)

    assert response.status_code == 200
    assert (
        await booth_zone_of(client, waitlist_world, waitlist_world.first_booking_id)
        == waitlist_world.upgrade_zone_id
    )
