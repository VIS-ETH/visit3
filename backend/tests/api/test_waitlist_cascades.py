from collections.abc import Awaitable, Callable

from httpx import AsyncClient, Response

from app.models.user import User
from tests.api.conftest import KpSetup


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


async def register(
    client: AsyncClient, headers: dict[str, str], event_id: str, zone_id: str
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/bookings/register",
        json={"booth_zone_id": zone_id, "confirm_profile": True},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def wait_for(
    client: AsyncClient, headers: dict[str, str], booking_id: str, zone_id: str
) -> None:
    response = await client.put(
        f"/api/kp/bookings/{booking_id}/upgrade-waitlist",
        json={"target_booth_zone_ids": [zone_id]},
        headers=headers,
    )
    assert response.status_code == 200, response.text


async def my_zone(client: AsyncClient, headers: dict[str, str], event_id: str) -> str:
    response = await client.get(
        f"/api/kp/events/{event_id}/my-booking", headers=headers
    )
    return response.json()["booth_zone_id"]


async def companies(
    names: tuple[str, ...],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> list[dict[str, str]]:
    result = []
    for name in names:
        user = await create_user(
            email=f"{name}@example.com", password=None, company_name=f"{name} AG"
        )
        headers = {**await auth_headers(user), **csrf_headers}
        await complete_company_profile(headers)
        result.append(headers)
    return result


async def test_a_promotion_frees_its_old_zone_for_the_next_waiting_booking(
    client: AsyncClient,
    kp_setup: KpSetup,
    president_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    event = kp_setup.event_id
    gold = await make_zone(client, president_headers, event, "Gold", "#AA0000", 1)
    silver = await make_zone(client, president_headers, event, "Silver", "#00AA00", 1)
    bronze = await make_zone(client, president_headers, event, "Bronze", "#0000AA", 1)
    alpha, beta, gamma = await companies(
        ("alpha", "beta", "gamma"),
        create_user,
        auth_headers,
        csrf_headers,
        complete_company_profile,
    )
    in_gold = await register(client, alpha, event, gold)
    in_silver = await register(client, beta, event, silver)
    in_bronze = await register(client, gamma, event, bronze)
    await wait_for(client, beta, in_silver, gold)
    await wait_for(client, gamma, in_bronze, silver)

    cancelled = await client.patch(
        f"/api/kp/bookings/{in_gold}/status",
        json={"status": "CANCELLED"},
        headers=alpha,
    )

    assert cancelled.status_code == 200, cancelled.text
    assert await my_zone(client, beta, event) == gold
    assert await my_zone(client, gamma, event) == silver


async def test_a_deleted_booking_in_a_waitlist_does_not_break_reading_it(
    client: AsyncClient,
    kp_setup: KpSetup,
    staff_headers: dict[str, str],
    president_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    event = kp_setup.event_id
    gold = await make_zone(client, president_headers, event, "Gold", "#AA0000", 1)
    silver = await make_zone(client, president_headers, event, "Silver", "#00AA00", 5)
    alpha, beta, gamma = await companies(
        ("alpha", "beta", "gamma"),
        create_user,
        auth_headers,
        csrf_headers,
        complete_company_profile,
    )
    await register(client, alpha, event, gold)
    first = await register(client, beta, event, silver)
    second = await register(client, gamma, event, silver)
    await wait_for(client, beta, first, gold)
    await wait_for(client, gamma, second, gold)

    deleted = await client.delete(f"/api/kp/bookings/{first}", headers=staff_headers)

    assert deleted.status_code < 300, deleted.text
    waitlist = await client.get(
        f"/api/kp/bookings/{second}/upgrade-waitlist", headers=gamma
    )
    assert waitlist.status_code == 200, waitlist.text
    assert [entry["position"] for entry in waitlist.json()] == [1]
