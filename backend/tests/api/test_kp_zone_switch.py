from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kp_event import (
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZoneServiceLink,
)
from app.models.user import User
from tests.api.conftest import KpSetup, kp_payload, move_event_into_the_past

INCLUDED_QUANTITY = 2
OTHER_COMPANY_EMAIL = "beta@example.com"
OTHER_COMPANY_NAME = "Beta GmbH"


@dataclass(frozen=True)
class SwitchWorld:
    event_id: str
    home_zone_id: str
    target_zone_id: str
    spare_zone_id: str
    booking_id: str
    company_headers: dict[str, str]
    staff_headers: dict[str, str]


@pytest.fixture
async def other_company_headers(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    user = await create_user(
        email=OTHER_COMPANY_EMAIL, password=None, company_name=OTHER_COMPANY_NAME
    )
    return {**await auth_headers(user), **csrf_headers}


async def create_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    event_id: str,
    *,
    name: str,
    color: str,
    capacity: int = 1,
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": name, "color": color, "capacity": capacity},
        headers=staff_headers,
    )
    return response.json()["id"]


async def switch_zone(
    client: AsyncClient, world: SwitchWorld, booth_zone_id: str
) -> Response:
    return await client.post(
        f"/api/kp/bookings/{world.booking_id}/switch-zone",
        json={"booth_zone_id": booth_zone_id},
        headers=world.company_headers,
    )


@pytest.fixture
async def switch_world(
    client: AsyncClient,
    db_session: AsyncSession,
    kp_setup: KpSetup,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
) -> SwitchWorld:
    booking = (await register_booking(company_headers, kp_setup)).json()
    target_zone_id = await create_zone(
        client, staff_headers, kp_setup.event_id, name="Gold", color="#AABBCC"
    )
    spare_zone_id = await create_zone(
        client, staff_headers, kp_setup.event_id, name="Silver", color="#CCBBAA"
    )
    db_session.add(
        KpEventBoothZoneServiceLink(
            booth_zone_id=UUID(target_zone_id),
            service_id=UUID(kp_setup.service_id),
            included_quantity=INCLUDED_QUANTITY,
        )
    )
    await db_session.commit()
    db_session.expunge_all()
    return SwitchWorld(
        event_id=kp_setup.event_id,
        home_zone_id=kp_setup.booth_zone_id,
        target_zone_id=target_zone_id,
        spare_zone_id=spare_zone_id,
        booking_id=booking["id"],
        company_headers=company_headers,
        staff_headers=staff_headers,
    )


async def add_waitlist_entries(
    db_session: AsyncSession, booking_id: str, target_booth_zone_ids: list[str]
) -> None:
    for priority_rank, target_booth_zone_id in enumerate(target_booth_zone_ids, 1):
        db_session.add(
            KpEventBookingUpgradeWaitlist(
                booking_id=UUID(booking_id),
                target_booth_zone_id=UUID(target_booth_zone_id),
                priority_rank=priority_rank,
            )
        )
    await db_session.commit()
    db_session.expunge_all()


async def test_switching_moves_the_booking_and_recomputes_inclusions(
    client: AsyncClient, switch_world: SwitchWorld
):
    await client.patch(
        f"/api/kp/bookings/{switch_world.booking_id}/booth-number",
        json={"booth_nr": 5},
        headers=switch_world.staff_headers,
    )

    response = await switch_zone(client, switch_world, switch_world.target_zone_id)

    assert response.status_code == 200
    body = response.json()
    assert body["booth_zone_id"] == switch_world.target_zone_id
    assert body["booth_nr"] is None
    assert body["status"] == "REGISTERED"
    assert [
        (service["quantity"], service["included_quantity"], service["charged_quantity"])
        for service in body["services"]
    ] == [(INCLUDED_QUANTITY, INCLUDED_QUANTITY, 0)]


async def test_switching_removes_only_the_waitlist_entry_of_the_new_zone(
    client: AsyncClient, db_session: AsyncSession, switch_world: SwitchWorld
):
    await add_waitlist_entries(
        db_session,
        switch_world.booking_id,
        [switch_world.target_zone_id, switch_world.spare_zone_id],
    )

    await switch_zone(client, switch_world, switch_world.target_zone_id)

    remaining = await client.get(
        f"/api/kp/bookings/{switch_world.booking_id}/upgrade-waitlist",
        headers=switch_world.company_headers,
    )
    assert [entry["target_booth_zone_id"] for entry in remaining.json()] == [
        switch_world.spare_zone_id
    ]


async def test_switching_to_the_current_zone_is_refused(
    client: AsyncClient, switch_world: SwitchWorld
):
    response = await switch_zone(client, switch_world, switch_world.home_zone_id)

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booking_zone_switch_not_allowed"


async def test_switching_is_refused_once_the_booking_is_confirmed(
    client: AsyncClient, switch_world: SwitchWorld
):
    await client.post(
        f"/api/kp/bookings/{switch_world.booking_id}/accept",
        headers=switch_world.staff_headers,
    )

    response = await switch_zone(client, switch_world, switch_world.target_zone_id)

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booking_zone_switch_not_allowed"


async def test_switching_is_refused_after_the_finalization_deadline(
    client: AsyncClient, db_session: AsyncSession, switch_world: SwitchWorld
):
    await move_event_into_the_past(db_session, switch_world.event_id)

    response = await switch_zone(client, switch_world, switch_world.target_zone_id)

    assert response.status_code == 403
    assert response.json()["code"] == "error.kp_finalization_deadline_passed"


async def test_switching_into_a_full_zone_is_refused(
    client: AsyncClient,
    switch_world: SwitchWorld,
    other_company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await complete_company_profile(other_company_headers)
    await client.post(
        f"/api/kp/events/{switch_world.event_id}/bookings/register",
        json={"booth_zone_id": switch_world.target_zone_id, "confirm_profile": True},
        headers=other_company_headers,
    )

    response = await switch_zone(client, switch_world, switch_world.target_zone_id)

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_zone_full"


async def test_switching_into_a_zone_of_another_event_is_refused(
    client: AsyncClient, switch_world: SwitchWorld
):
    other_event = await client.post(
        "/api/kp/create",
        json=kp_payload("Other Kontaktparty"),
        headers=switch_world.staff_headers,
    )
    foreign_zone_id = await create_zone(
        client,
        switch_world.staff_headers,
        other_event.json()["id"],
        name="Foreign hall",
        color="#123456",
    )

    response = await switch_zone(client, switch_world, foreign_zone_id)

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_booth_zone_event_mismatch"


async def test_switching_into_an_unknown_zone_is_refused(
    client: AsyncClient, switch_world: SwitchWorld
):
    response = await switch_zone(
        client, switch_world, "00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.kp_booth_zone_not_found"


async def test_switching_into_a_zone_without_inclusions_respects_the_service_stock(
    client: AsyncClient, switch_world: SwitchWorld, kp_setup: KpSetup
):
    await switch_zone(client, switch_world, switch_world.target_zone_id)
    await client.patch(
        f"/api/kp/services/{kp_setup.service_id}",
        json={"max_total_quantity": 1},
        headers=switch_world.staff_headers,
    )

    response = await switch_zone(client, switch_world, switch_world.spare_zone_id)

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_service_quantity_invalid"
    booking = await client.get(
        f"/api/kp/events/{switch_world.event_id}/my-booking",
        headers=switch_world.company_headers,
    )
    assert booking.json()["booth_zone_id"] == switch_world.target_zone_id
