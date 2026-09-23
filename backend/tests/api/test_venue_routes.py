from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.kp_event import KpEventBoothZone
from tests.api.conftest import KpSetup, kp_payload

TRIANGLE = {"type": "polygon", "points": [[10, 10], [200, 10], [200, 120]]}
SQUARE = {"type": "rect", "x": 300, "y": 300, "w": 120, "h": 80}


async def create_layout(
    client: AsyncClient,
    staff_headers: dict[str, str],
    event_id: str,
    **overrides: Any,
) -> Response:
    return await client.post(
        f"/api/kp/events/{event_id}/venue-layouts",
        json={"name": "Einstein", **overrides},
        headers=staff_headers,
    )


async def put_shapes(
    client: AsyncClient,
    staff_headers: dict[str, str],
    layout_id: str,
    shapes: list[dict[str, Any]],
) -> Response:
    return await client.put(
        f"/api/kp/venue-layouts/{layout_id}/shapes",
        json={"shapes": shapes},
        headers=staff_headers,
    )


async def put_booths(
    client: AsyncClient,
    staff_headers: dict[str, str],
    layout_id: str,
    booths: list[dict[str, Any]],
) -> Response:
    return await client.put(
        f"/api/kp/venue-layouts/{layout_id}/booths",
        json={"booths": booths},
        headers=staff_headers,
    )


@pytest.fixture
async def layout_id(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
) -> str:
    response = await create_layout(client, staff_headers, kp_setup.event_id)
    return response.json()["id"]


@pytest.fixture
async def other_event_zone_id(
    client: AsyncClient, staff_headers: dict[str, str]
) -> str:
    event = await client.post(
        "/api/kp/create", json=kp_payload("Polymensa KP"), headers=staff_headers
    )
    zone = await client.post(
        f"/api/kp/events/{event.json()['id']}/booth-zones",
        json={"name": "Foreign hall", "capacity": 1, "color": "#123456"},
        headers=staff_headers,
    )
    return zone.json()["id"]


async def test_layout_is_created_with_the_default_abstract_bounds(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await create_layout(client, staff_headers, kp_setup.event_id)

    assert response.status_code == 200
    layout = response.json()
    assert layout["name"] == "Einstein"
    assert (layout["width"], layout["height"]) == (1000, 700)
    assert layout["is_active"] is True
    assert layout["background_url"] is None
    assert layout["zone_shapes"] == []
    assert layout["booths"] == []


async def test_layout_name_is_unique_per_event(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    await create_layout(client, staff_headers, kp_setup.event_id)

    response = await create_layout(client, staff_headers, kp_setup.event_id)

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_venue_layout_name_exists"


async def test_layouts_are_listed_in_order(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    await create_layout(client, staff_headers, kp_setup.event_id, name="Zweistein")
    await create_layout(
        client, staff_headers, kp_setup.event_id, name="Einstein", order=1
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue-layouts", headers=staff_headers
    )

    assert response.status_code == 200
    assert [layout["name"] for layout in response.json()] == ["Einstein", "Zweistein"]


async def test_layout_bounds_can_be_updated(
    client: AsyncClient, staff_headers: dict[str, str], layout_id: str
):
    response = await client.patch(
        f"/api/kp/venue-layouts/{layout_id}",
        json={"width": 2000, "height": 1400, "is_active": False},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert (response.json()["width"], response.json()["height"]) == (2000, 1400)
    assert response.json()["is_active"] is False


async def test_deleted_layout_disappears_from_the_list(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    deleted = await client.delete(
        f"/api/kp/venue-layouts/{layout_id}", headers=staff_headers
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue-layouts", headers=staff_headers
    )

    assert deleted.status_code == 200
    assert response.json() == []


async def test_shapes_replace_the_previous_ones(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    first = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}],
    )

    response = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [
            {
                "booth_zone_id": kp_setup.booth_zone_id,
                "shape": SQUARE,
                "label_position": [350, 340],
            }
        ],
    )

    assert first.status_code == 200
    assert response.status_code == 200
    shapes = response.json()["zone_shapes"]
    assert len(shapes) == 1
    assert shapes[0]["shape"] == SQUARE
    assert shapes[0]["label_position"] == [350, 340]
    assert shapes[0]["id"] != first.json()["zone_shapes"][0]["id"]


async def test_polygon_shape_round_trips_its_points(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    response = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}],
    )

    assert response.status_code == 200
    assert response.json()["zone_shapes"][0]["shape"] == TRIANGLE
    assert response.json()["zone_shapes"][0]["label_position"] is None


@pytest.mark.parametrize(
    "shape",
    [
        {"type": "polygon", "points": [[10, 10], [1200, 10], [200, 120]]},
        {"type": "polygon", "points": [[10, 10], [200, 10], [200, -1]]},
        {"type": "rect", "x": 900, "y": 300, "w": 200, "h": 80},
    ],
)
async def test_shape_outside_the_layout_bounds_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
    shape: dict[str, Any],
):
    response = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": shape}],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_venue_out_of_bounds"


async def test_label_position_outside_the_layout_bounds_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    response = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [
            {
                "booth_zone_id": kp_setup.booth_zone_id,
                "shape": TRIANGLE,
                "label_position": [10, 900],
            }
        ],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_venue_out_of_bounds"


async def test_polygon_with_two_points_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    response = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [
            {
                "booth_zone_id": kp_setup.booth_zone_id,
                "shape": {"type": "polygon", "points": [[10, 10], [200, 10]]},
            }
        ],
    )

    assert response.status_code == 422


async def test_shape_zone_of_another_event_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    layout_id: str,
    other_event_zone_id: str,
):
    response = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": other_event_zone_id, "shape": TRIANGLE}],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_booth_zone_event_mismatch"


async def test_shape_of_an_unknown_zone_is_rejected(
    client: AsyncClient, staff_headers: dict[str, str], layout_id: str
):
    response = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [
            {
                "booth_zone_id": "00000000-0000-0000-0000-000000000001",
                "shape": TRIANGLE,
            }
        ],
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.kp_booth_zone_not_found"


async def test_a_rejected_shape_batch_leaves_the_previous_shapes_in_place(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
    other_event_zone_id: str,
):
    await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}],
    )

    rejected = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [
            {"booth_zone_id": kp_setup.booth_zone_id, "shape": SQUARE},
            {"booth_zone_id": other_event_zone_id, "shape": TRIANGLE},
        ],
    )
    layouts = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue-layouts", headers=staff_headers
    )

    assert rejected.status_code == 400
    assert [shape["shape"] for shape in layouts.json()[0]["zone_shapes"]] == [TRIANGLE]


async def test_booths_replace_the_previous_ones(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    first = await put_booths(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "booth_nr": 1, "x": 20, "y": 30}],
    )

    response = await put_booths(
        client,
        staff_headers,
        layout_id,
        [
            {
                "booth_zone_id": kp_setup.booth_zone_id,
                "booth_nr": 1,
                "x": 40,
                "y": 50,
                "rotation": 90,
            },
            {
                "booth_zone_id": kp_setup.booth_zone_id,
                "booth_nr": 2,
                "x": 60,
                "y": 70,
            },
        ],
    )

    assert first.status_code == 200
    assert response.status_code == 200
    booths = response.json()["booths"]
    assert [booth["booth_nr"] for booth in booths] == [1, 2]
    assert (booths[0]["x"], booths[0]["y"], booths[0]["rotation"]) == (40, 50, 90)
    assert booths[1]["rotation"] is None


async def test_duplicate_booth_numbers_are_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    response = await put_booths(
        client,
        staff_headers,
        layout_id,
        [
            {"booth_zone_id": kp_setup.booth_zone_id, "booth_nr": 7, "x": 10, "y": 10},
            {"booth_zone_id": kp_setup.booth_zone_id, "booth_nr": 7, "x": 20, "y": 20},
        ],
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_venue_booth_number_duplicate"


async def test_booth_outside_the_layout_bounds_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    response = await put_booths(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "booth_nr": 1, "x": 10, "y": 800}],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_venue_out_of_bounds"


async def test_booth_zone_of_another_event_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    layout_id: str,
    other_event_zone_id: str,
):
    response = await put_booths(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": other_event_zone_id, "booth_nr": 1, "x": 10, "y": 10}],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_booth_zone_event_mismatch"


async def test_the_same_booth_number_can_be_reused_in_another_layout(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    second = await create_layout(
        client, staff_headers, kp_setup.event_id, name="Zweistein"
    )
    booth = {"booth_zone_id": kp_setup.booth_zone_id, "booth_nr": 1, "x": 10, "y": 10}

    first_response = await put_booths(client, staff_headers, layout_id, [booth])
    second_response = await put_booths(
        client, staff_headers, second.json()["id"], [booth]
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200


async def test_venue_zones_match_the_available_booth_zones(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)
    await client.put(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}/layout-file",
        files={"file": ("layout.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        headers=staff_headers,
    )

    venue = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue", headers=company_headers
    )
    available = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones/available",
        headers=company_headers,
    )

    assert venue.json()["zones"] == available.json()
    assert available.json()[0]["layout_url"] == "https://storage.test/download"
    assert available.json()[0]["available_spots"] == 4


async def test_company_venue_read_feeds_the_map_in_one_call(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}],
    )
    await put_booths(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "booth_nr": 1, "x": 10, "y": 10}],
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue", headers=company_headers
    )

    assert response.status_code == 200
    venue = response.json()
    assert venue["event_id"] == kp_setup.event_id
    assert venue["own_booking"] is None
    assert [layout["name"] for layout in venue["layouts"]] == ["Einstein"]
    assert venue["layouts"][0]["zone_shapes"][0]["shape"] == TRIANGLE
    assert venue["layouts"][0]["booths"][0]["is_own_booking"] is False
    assert [zone["name"] for zone in venue["zones"]] == ["Main hall"]
    assert venue["zones"][0]["available_spots"] == 5
    assert venue["zones"][0]["color"] == "#000000"


async def test_company_venue_read_flags_the_own_booth(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)
    await client.patch(
        f"/api/kp/bookings/{booking.json()['id']}/booth-number",
        json={"booth_nr": 2},
        headers=staff_headers,
    )
    await put_booths(
        client,
        staff_headers,
        layout_id,
        [
            {
                "booth_zone_id": kp_setup.booth_zone_id,
                "booth_nr": 1,
                "x": 10,
                "y": 10,
            },
            {
                "booth_zone_id": kp_setup.booth_zone_id,
                "booth_nr": 2,
                "x": 40,
                "y": 10,
            },
        ],
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue", headers=company_headers
    )

    venue = response.json()
    assert venue["own_booking"]["booth_nr"] == 2
    assert venue["own_booking"]["booking_id"] == booking.json()["id"]
    assert [booth["is_own_booking"] for booth in venue["layouts"][0]["booths"]] == [
        False,
        True,
    ]


async def test_company_venue_read_hides_inactive_layouts(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    await client.patch(
        f"/api/kp/venue-layouts/{layout_id}",
        json={"is_active": False},
        headers=staff_headers,
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue", headers=company_headers
    )

    assert response.status_code == 200
    assert response.json()["layouts"] == []


async def test_deleting_a_zone_removes_its_shapes_and_booths(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}],
    )
    await put_booths(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "booth_nr": 1, "x": 10, "y": 10}],
    )

    deleted = await client.delete(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}", headers=staff_headers
    )
    staff_layouts = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue-layouts", headers=staff_headers
    )
    venue = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue", headers=company_headers
    )

    assert deleted.status_code == 200
    assert staff_layouts.json()[0]["zone_shapes"] == []
    assert staff_layouts.json()[0]["booths"] == []
    assert venue.json()["layouts"][0]["zone_shapes"] == []
    assert venue.json()["layouts"][0]["booths"] == []


async def test_shapes_of_a_zone_deleted_in_the_database_stay_hidden(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}],
    )
    statement = select(KpEventBoothZone).where(
        col(KpEventBoothZone.id) == UUID(kp_setup.booth_zone_id)
    )
    zone = (await db_session.execute(statement)).scalar_one()
    zone.mark_deleted()
    db_session.add(zone)
    await db_session.commit()

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue", headers=company_headers
    )

    assert response.status_code == 200
    assert response.json()["layouts"][0]["zone_shapes"] == []


async def test_venue_read_reports_an_unknown_event(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.get(
        "/api/kp/events/00000000-0000-0000-0000-000000000001/venue",
        headers=company_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.kp_event_not_found"


async def test_cloning_an_event_copies_layouts_shapes_and_booths(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    await put_shapes(
        client,
        staff_headers,
        layout_id,
        [
            {
                "booth_zone_id": kp_setup.booth_zone_id,
                "shape": TRIANGLE,
                "label_position": [100, 50],
            }
        ],
    )
    await put_booths(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "booth_nr": 3, "x": 15, "y": 25}],
    )

    clone = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/clone",
        json=kp_payload("Einstein clone"),
        headers=staff_headers,
    )
    layouts = await client.get(
        f"/api/kp/events/{clone.json()['id']}/venue-layouts", headers=staff_headers
    )
    zones = await client.get(
        f"/api/kp/events/{clone.json()['id']}/booth-zones", headers=staff_headers
    )

    assert clone.status_code == 200
    assert layouts.status_code == 200
    cloned_layout = layouts.json()[0]
    cloned_zone_id = zones.json()[0]["id"]
    assert cloned_layout["name"] == "Einstein"
    assert cloned_layout["id"] != layout_id
    assert cloned_layout["background_url"] is None
    assert cloned_layout["zone_shapes"][0]["shape"] == TRIANGLE
    assert cloned_layout["zone_shapes"][0]["label_position"] == [100, 50]
    assert cloned_layout["zone_shapes"][0]["booth_zone_id"] == cloned_zone_id
    assert cloned_layout["booths"][0]["booth_nr"] == 3
    assert cloned_layout["booths"][0]["booth_zone_id"] == cloned_zone_id


async def test_cloning_an_event_leaves_the_source_layout_untouched(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}],
    )

    await client.post(
        f"/api/kp/events/{kp_setup.event_id}/clone",
        json=kp_payload("Einstein clone"),
        headers=staff_headers,
    )
    layouts = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/venue-layouts", headers=staff_headers
    )

    assert [layout["id"] for layout in layouts.json()] == [layout_id]
    assert layouts.json()[0]["zone_shapes"][0]["booth_zone_id"] == (
        kp_setup.booth_zone_id
    )


async def test_shapes_of_an_unknown_layout_are_reported(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await put_shapes(
        client, staff_headers, "00000000-0000-0000-0000-000000000001", []
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.kp_venue_layout_not_found"


async def test_polygon_with_too_many_points_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    shape = {
        "type": "polygon",
        "points": [[index % 100, index % 100] for index in range(201)],
    }

    response = await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": shape}],
    )

    assert response.status_code == 422
    assert response.json()["code"] == "error.validation_failed"


async def test_too_many_shapes_are_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    shape = {"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}

    response = await put_shapes(client, staff_headers, layout_id, [shape] * 501)

    assert response.status_code == 422
    assert response.json()["code"] == "error.validation_failed"


async def test_too_many_booths_are_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    booths = [
        {
            "booth_zone_id": kp_setup.booth_zone_id,
            "booth_nr": index + 1,
            "x": 10,
            "y": 10,
        }
        for index in range(501)
    ]

    response = await put_booths(client, staff_headers, layout_id, booths)

    assert response.status_code == 422
    assert response.json()["code"] == "error.validation_failed"


async def test_shrinking_a_layout_below_its_shapes_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}],
    )

    response = await client.patch(
        f"/api/kp/venue-layouts/{layout_id}",
        json={"width": 100},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_venue_out_of_bounds"


async def test_shrinking_a_layout_below_its_booths_is_rejected(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    await put_booths(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "booth_nr": 1, "x": 400, "y": 50}],
    )

    response = await client.patch(
        f"/api/kp/venue-layouts/{layout_id}",
        json={"width": 300},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_venue_out_of_bounds"


async def test_growing_a_layout_keeps_its_shapes(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    layout_id: str,
):
    await put_shapes(
        client,
        staff_headers,
        layout_id,
        [{"booth_zone_id": kp_setup.booth_zone_id, "shape": TRIANGLE}],
    )

    response = await client.patch(
        f"/api/kp/venue-layouts/{layout_id}",
        json={"width": 2000, "height": 1400},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["zone_shapes"][0]["shape"] == TRIANGLE
