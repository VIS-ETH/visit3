from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import pytest
from httpx import AsyncClient, Response

from app.models.user import User
from tests.api.conftest import KpSetup

FULL_ZONE_CAPACITY = 1


@dataclass(frozen=True)
class WaitlistApiWorld:
    event_id: str
    home_zone_id: str
    full_zone_id: str
    open_zone_id: str
    first_booking_id: str
    second_booking_id: str
    first_headers: dict[str, str]
    second_headers: dict[str, str]
    staff_headers: dict[str, str]


@pytest.fixture
def make_company_headers(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> Callable[[str], Awaitable[dict[str, str]]]:
    async def _make_company_headers(name: str) -> dict[str, str]:
        user = await create_user(
            email=f"{name}@example.com", password=None, company_name=f"{name} AG"
        )
        return {**await auth_headers(user), **csrf_headers}

    return _make_company_headers


async def create_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    event_id: str,
    *,
    name: str,
    color: str,
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": name, "color": color, "capacity": FULL_ZONE_CAPACITY},
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


async def put_waitlist(
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


async def get_waitlist(
    client: AsyncClient, headers: dict[str, str], booking_id: str
) -> Response:
    return await client.get(
        f"/api/kp/bookings/{booking_id}/upgrade-waitlist", headers=headers
    )


async def get_staff_waitlist(
    client: AsyncClient, headers: dict[str, str], booking_id: str
) -> Response:
    return await client.get(
        f"/api/kp/staff/bookings/{booking_id}/upgrade-waitlist", headers=headers
    )


@pytest.fixture
async def plain_staff_headers(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    user = await create_user(
        email="waitlist-staff@example.com",
        password=None,
        is_staff=True,
        is_company=False,
    )
    return {**await auth_headers(user), **csrf_headers}


@pytest.fixture
async def waitlist_api_world(
    client: AsyncClient,
    kp_setup: KpSetup,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    make_company_headers: Callable[[str], Awaitable[dict[str, str]]],
) -> WaitlistApiWorld:
    full_zone_id = await create_zone(
        client, staff_headers, kp_setup.event_id, name="Gold", color="#AABBCC"
    )
    open_zone_id = await create_zone(
        client, staff_headers, kp_setup.event_id, name="Silver", color="#CCBBAA"
    )
    second_headers = await make_company_headers("second")
    holder_headers = await make_company_headers("holder")

    await register_into(
        client,
        complete_company_profile,
        holder_headers,
        kp_setup.event_id,
        full_zone_id,
    )
    first_booking_id = await register_into(
        client,
        complete_company_profile,
        company_headers,
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
    await put_waitlist(client, company_headers, first_booking_id, [full_zone_id])
    await put_waitlist(client, second_headers, second_booking_id, [full_zone_id])

    return WaitlistApiWorld(
        event_id=kp_setup.event_id,
        home_zone_id=kp_setup.booth_zone_id,
        full_zone_id=full_zone_id,
        open_zone_id=open_zone_id,
        first_booking_id=first_booking_id,
        second_booking_id=second_booking_id,
        first_headers=company_headers,
        second_headers=second_headers,
        staff_headers=staff_headers,
    )


async def test_waitlist_reports_availability_and_queue_position(
    client: AsyncClient, waitlist_api_world: WaitlistApiWorld
):
    first = await get_waitlist(
        client, waitlist_api_world.first_headers, waitlist_api_world.first_booking_id
    )
    second = await get_waitlist(
        client, waitlist_api_world.second_headers, waitlist_api_world.second_booking_id
    )

    assert [
        (entry["available_spots"], entry["position"]) for entry in first.json()
    ] == [(0, 1)]
    assert [
        (entry["available_spots"], entry["position"]) for entry in second.json()
    ] == [(0, 2)]


async def test_staff_reads_the_waitlist_of_a_booking_of_any_company(
    client: AsyncClient,
    waitlist_api_world: WaitlistApiWorld,
    plain_staff_headers: dict[str, str],
):
    owner = await get_waitlist(
        client, waitlist_api_world.first_headers, waitlist_api_world.first_booking_id
    )
    staff = await get_staff_waitlist(
        client, plain_staff_headers, waitlist_api_world.first_booking_id
    )

    assert staff.status_code == 200
    assert staff.json() == owner.json()


async def test_company_cannot_read_the_staff_waitlist(
    client: AsyncClient, waitlist_api_world: WaitlistApiWorld
):
    response = await get_staff_waitlist(
        client, waitlist_api_world.first_headers, waitlist_api_world.first_booking_id
    )

    assert response.status_code == 403


async def test_queue_position_ignores_entries_of_inactive_bookings(
    client: AsyncClient, waitlist_api_world: WaitlistApiWorld
):
    await client.patch(
        f"/api/kp/bookings/{waitlist_api_world.first_booking_id}/status",
        json={"status": "CANCELLED"},
        headers=waitlist_api_world.first_headers,
    )

    second = await get_waitlist(
        client, waitlist_api_world.second_headers, waitlist_api_world.second_booking_id
    )

    assert [entry["position"] for entry in second.json()] == [1]


async def test_waitlist_refuses_a_zone_that_still_has_free_spots(
    client: AsyncClient, waitlist_api_world: WaitlistApiWorld
):
    response = await put_waitlist(
        client,
        waitlist_api_world.first_headers,
        waitlist_api_world.first_booking_id,
        [waitlist_api_world.open_zone_id],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_waitlist_zone_has_capacity"


async def test_waitlist_refuses_the_current_zone(
    client: AsyncClient, waitlist_api_world: WaitlistApiWorld
):
    response = await put_waitlist(
        client,
        waitlist_api_world.first_headers,
        waitlist_api_world.first_booking_id,
        [waitlist_api_world.home_zone_id],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_waitlist_same_zone"


async def test_waitlist_answer_reports_the_new_entries(
    client: AsyncClient, waitlist_api_world: WaitlistApiWorld
):
    response = await put_waitlist(
        client,
        waitlist_api_world.second_headers,
        waitlist_api_world.second_booking_id,
        [waitlist_api_world.full_zone_id],
    )

    assert response.status_code == 200
    assert [
        (entry["target_booth_zone_id"], entry["priority_rank"], entry["position"])
        for entry in response.json()
    ] == [(waitlist_api_world.full_zone_id, 1, 2)]
