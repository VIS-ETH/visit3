import csv
import io
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response

from app.models.user import User
from tests.api.conftest import KpSetup, kp_payload


@dataclass(frozen=True)
class ZoneWorld:
    event_id: str
    main_id: str
    side_id: str
    annex_id: str


async def create_zone(
    client: AsyncClient,
    headers: dict[str, str],
    event_id: str,
    name: str,
    color: str,
    **overrides: object,
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": name, "color": color, "capacity": 3, **overrides},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["id"]


async def reorder(
    client: AsyncClient, headers: dict[str, str], event_id: str, zone_ids: list[str]
) -> Response:
    return await client.put(
        f"/api/kp/events/{event_id}/booth-zones/order",
        json={"booth_zone_ids": zone_ids},
        headers=headers,
    )


async def staff_zone_names(
    client: AsyncClient, headers: dict[str, str], event_id: str
) -> list[str]:
    response = await client.get(
        f"/api/kp/events/{event_id}/booth-zones", headers=headers
    )
    return [zone["name"] for zone in response.json()]


@pytest.fixture
async def zone_world(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
) -> ZoneWorld:
    side_id = await create_zone(
        client, staff_headers, kp_setup.event_id, "Side hall", "#ABCDEF"
    )
    annex_id = await create_zone(
        client, staff_headers, kp_setup.event_id, "Annex", "#123456"
    )
    return ZoneWorld(
        event_id=kp_setup.event_id,
        main_id=kp_setup.booth_zone_id,
        side_id=side_id,
        annex_id=annex_id,
    )


async def test_reorder_returns_the_zones_in_the_new_order(
    client: AsyncClient, staff_headers: dict[str, str], zone_world: ZoneWorld
):
    new_order = [zone_world.side_id, zone_world.annex_id, zone_world.main_id]

    response = await reorder(client, staff_headers, zone_world.event_id, new_order)

    assert response.status_code == 200
    assert [zone["id"] for zone in response.json()] == new_order
    assert [zone["order"] for zone in response.json()] == [0, 1, 2]


async def test_staff_listing_follows_the_new_order(
    client: AsyncClient, staff_headers: dict[str, str], zone_world: ZoneWorld
):
    await reorder(
        client,
        staff_headers,
        zone_world.event_id,
        [zone_world.annex_id, zone_world.main_id, zone_world.side_id],
    )

    assert await staff_zone_names(client, staff_headers, zone_world.event_id) == [
        "Annex",
        "Main hall",
        "Side hall",
    ]


async def test_companies_see_the_zones_in_the_new_order(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    zone_world: ZoneWorld,
):
    new_order = [zone_world.side_id, zone_world.main_id, zone_world.annex_id]
    await reorder(client, staff_headers, zone_world.event_id, new_order)

    response = await client.get(
        f"/api/kp/events/{zone_world.event_id}/booth-zones/available",
        headers=company_headers,
    )

    assert response.status_code == 200
    assert [zone["id"] for zone in response.json()] == new_order


async def test_venue_map_lists_the_zones_in_the_new_order(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    zone_world: ZoneWorld,
):
    new_order = [zone_world.annex_id, zone_world.side_id, zone_world.main_id]
    await reorder(client, staff_headers, zone_world.event_id, new_order)

    response = await client.get(
        f"/api/kp/events/{zone_world.event_id}/venue", headers=company_headers
    )

    assert response.status_code == 200
    assert [zone["id"] for zone in response.json()["zones"]] == new_order


async def test_capacity_export_follows_the_new_order(
    client: AsyncClient, staff_headers: dict[str, str], zone_world: ZoneWorld
):
    await reorder(
        client,
        staff_headers,
        zone_world.event_id,
        [zone_world.side_id, zone_world.annex_id, zone_world.main_id],
    )

    response = await client.get(
        f"/api/kp/events/{zone_world.event_id}/exports/booth-zone-capacity/download",
        headers=staff_headers,
    )

    rows = csv.DictReader(
        io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"
    )
    assert [row["zone"] for row in rows] == ["Side hall", "Annex", "Main hall"]


async def test_zones_with_the_same_order_are_listed_by_name(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    for name, color in (("Zeta", "#000011"), ("Alpha", "#000022")):
        await create_zone(
            client, staff_headers, kp_setup.event_id, name, color, order=100
        )

    assert await staff_zone_names(client, staff_headers, kp_setup.event_id) == [
        "Alpha",
        "Main hall",
        "Zeta",
    ]


async def test_a_new_zone_is_listed_after_the_reordered_zones(
    client: AsyncClient, staff_headers: dict[str, str], zone_world: ZoneWorld
):
    await reorder(
        client,
        staff_headers,
        zone_world.event_id,
        [zone_world.side_id, zone_world.annex_id, zone_world.main_id],
    )

    await create_zone(client, staff_headers, zone_world.event_id, "Aula", "#654321")

    assert await staff_zone_names(client, staff_headers, zone_world.event_id) == [
        "Side hall",
        "Annex",
        "Main hall",
        "Aula",
    ]


@pytest.mark.parametrize(
    "build_order",
    [
        pytest.param(lambda world, _: [world.main_id, world.side_id], id="missing"),
        pytest.param(
            lambda world, _: [world.main_id, world.side_id, world.side_id],
            id="duplicate",
        ),
        pytest.param(
            lambda world, _: [
                world.main_id,
                world.side_id,
                world.annex_id,
                world.annex_id,
            ],
            id="duplicate-extra",
        ),
        pytest.param(
            lambda world, _: [world.main_id, world.side_id, str(uuid4())],
            id="unknown",
        ),
        pytest.param(
            lambda world, foreign_id: [
                world.main_id,
                world.side_id,
                world.annex_id,
                foreign_id,
            ],
            id="foreign",
        ),
        pytest.param(lambda *_: [], id="empty"),
    ],
)
async def test_invalid_orders_are_rejected_without_changes(
    client: AsyncClient,
    staff_headers: dict[str, str],
    zone_world: ZoneWorld,
    build_order: Callable[[ZoneWorld, str], list[str]],
):
    other_event = await client.post(
        "/api/kp/create", json=kp_payload("Other party"), headers=staff_headers
    )
    foreign_id = await create_zone(
        client, staff_headers, other_event.json()["id"], "Foreign", "#FEDCBA"
    )
    before = await staff_zone_names(client, staff_headers, zone_world.event_id)

    response = await reorder(
        client, staff_headers, zone_world.event_id, build_order(zone_world, foreign_id)
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_booth_zone_order_invalid"
    assert await staff_zone_names(client, staff_headers, zone_world.event_id) == before


async def test_deleted_zones_cannot_be_ordered(
    client: AsyncClient, staff_headers: dict[str, str], zone_world: ZoneWorld
):
    await client.delete(
        f"/api/kp/booth-zones/{zone_world.annex_id}", headers=staff_headers
    )

    rejected = await reorder(
        client,
        staff_headers,
        zone_world.event_id,
        [zone_world.annex_id, zone_world.side_id, zone_world.main_id],
    )
    accepted = await reorder(
        client,
        staff_headers,
        zone_world.event_id,
        [zone_world.side_id, zone_world.main_id],
    )

    assert rejected.status_code == 400
    assert accepted.status_code == 200
    assert await staff_zone_names(client, staff_headers, zone_world.event_id) == [
        "Side hall",
        "Main hall",
    ]


async def test_reordering_an_unknown_event_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await reorder(client, staff_headers, str(uuid4()), [])

    assert response.status_code == 404
    assert response.json()["code"] == "error.kp_event_not_found"


async def test_companies_cannot_reorder_zones(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    zone_world: ZoneWorld,
):
    before = await staff_zone_names(client, staff_headers, zone_world.event_id)

    response = await reorder(
        client,
        company_headers,
        zone_world.event_id,
        [zone_world.side_id, zone_world.annex_id, zone_world.main_id],
    )

    assert response.status_code == 403
    assert await staff_zone_names(client, staff_headers, zone_world.event_id) == before


async def test_staff_without_president_role_cannot_reorder_zones(
    client: AsyncClient,
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    zone_world: ZoneWorld,
):
    headers = {**await auth_headers(staff_user), **csrf_headers}

    response = await reorder(
        client,
        headers,
        zone_world.event_id,
        [zone_world.side_id, zone_world.annex_id, zone_world.main_id],
    )

    assert response.status_code == 403
