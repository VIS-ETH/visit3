from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from httpx import AsyncClient, Response

from app.models.kp_event import MAX_SERVICE_QUANTITY
from app.models.user import User
from tests.api.conftest import MAX_QUANTITY_PER_BOOKING, KpSetup, kp_payload

BOOTH_ELEMENT = "BOOTH_ELEMENT"
SERVICE = "SERVICE"
OTHER_COMPANY_EMAIL = "beta@example.com"
OTHER_COMPANY_NAME = "Beta GmbH"
LAYOUT_DESCRIPTION = "Two tables along the wall, one standing table in front."


async def create_service(
    client: AsyncClient,
    staff_headers: dict[str, str],
    event_id: str,
    **overrides: Any,
) -> Response:
    return await client.post(
        f"/api/kp/events/{event_id}/services",
        json={"name": "Tisch", **overrides},
        headers=staff_headers,
    )


async def create_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    event_id: str,
    **overrides: Any,
) -> Response:
    return await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": "Side hall", "color": "#ABCDEF", "capacity": 2, **overrides},
        headers=staff_headers,
    )


async def register_in_zone(
    client: AsyncClient,
    headers: dict[str, str],
    event_id: str,
    booth_zone_id: str,
    services: list[dict[str, Any]],
) -> Response:
    return await client.post(
        f"/api/kp/events/{event_id}/bookings/register",
        json={
            "booth_zone_id": booth_zone_id,
            "services": services,
            "confirm_profile": True,
        },
        headers=headers,
    )


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


async def test_booth_element_keeps_its_category_and_unit_label(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await create_service(
        client,
        staff_headers,
        kp_setup.event_id,
        category=BOOTH_ELEMENT,
        unit_label="Stück",
        max_quantity_per_booking=4,
    )

    assert response.status_code == 200
    assert response.json()["category"] == BOOTH_ELEMENT
    assert response.json()["unit_label"] == "Stück"


async def test_a_service_belongs_to_the_service_category_by_default(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/services", headers=staff_headers
    )

    assert response.status_code == 200
    assert [service["category"] for service in response.json()] == [SERVICE]
    assert [service["unit_label"] for service in response.json()] == [None]


async def test_a_service_can_be_turned_into_a_booth_element(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.patch(
        f"/api/kp/services/{kp_setup.service_id}",
        json={"category": BOOTH_ELEMENT, "unit_label": "Stück"},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["category"] == BOOTH_ELEMENT
    assert response.json()["unit_label"] == "Stück"


async def test_available_services_are_filtered_by_category(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
):
    element = await create_service(
        client, staff_headers, kp_setup.event_id, category=BOOTH_ELEMENT
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/services/available",
        params={"category": BOOTH_ELEMENT},
        headers=company_headers,
    )

    assert response.status_code == 200
    assert [service["id"] for service in response.json()] == [element.json()["id"]]


async def test_available_services_without_a_filter_return_every_category(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
):
    element = await create_service(
        client, staff_headers, kp_setup.event_id, category=BOOTH_ELEMENT
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/services/available",
        headers=company_headers,
    )

    assert response.status_code == 200
    assert {service["id"] for service in response.json()} == {
        kp_setup.service_id,
        element.json()["id"],
    }


async def test_zone_is_created_with_its_included_services(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[
            {"service_id": kp_setup.service_id, "included_quantity": 2},
        ],
    )

    assert response.status_code == 200
    assert response.json()["included_services"] == [
        {"service_id": kp_setup.service_id, "included_quantity": 2}
    ]


async def test_updating_a_zone_replaces_its_included_services(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    element = await create_service(
        client,
        staff_headers,
        kp_setup.event_id,
        category=BOOTH_ELEMENT,
        max_quantity_per_booking=4,
    )
    zone = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[{"service_id": kp_setup.service_id, "included_quantity": 2}],
    )

    response = await client.patch(
        f"/api/kp/booth-zones/{zone.json()['id']}",
        json={
            "included_services": [
                {"service_id": element.json()["id"], "included_quantity": 4}
            ]
        },
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["included_services"] == [
        {"service_id": element.json()["id"], "included_quantity": 4}
    ]


async def test_updating_a_zone_without_the_list_keeps_its_included_services(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    zone = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[{"service_id": kp_setup.service_id, "included_quantity": 2}],
    )

    response = await client.patch(
        f"/api/kp/booth-zones/{zone.json()['id']}",
        json={"capacity": 7},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["included_services"] == [
        {"service_id": kp_setup.service_id, "included_quantity": 2}
    ]


async def test_an_empty_list_clears_the_included_services(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    zone = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[{"service_id": kp_setup.service_id, "included_quantity": 2}],
    )

    response = await client.patch(
        f"/api/kp/booth-zones/{zone.json()['id']}",
        json={"included_services": []},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["included_services"] == []


async def test_an_included_service_must_belong_to_the_event(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    other_event = await client.post(
        "/api/kp/create", json=kp_payload("Polymensa KP"), headers=staff_headers
    )
    foreign = await create_service(
        client, staff_headers, other_event.json()["id"], name="Foreign table"
    )

    response = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[
            {"service_id": foreign.json()["id"], "included_quantity": 1}
        ],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_service_event_mismatch"


async def test_an_included_service_must_exist(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[
            {
                "service_id": "11111111-1111-1111-1111-111111111111",
                "included_quantity": 1,
            }
        ],
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.kp_service_not_found"


async def test_a_service_cannot_be_included_twice(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[
            {"service_id": kp_setup.service_id, "included_quantity": 1},
            {"service_id": kp_setup.service_id, "included_quantity": 2},
        ],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_included_service_duplicate"


async def test_included_quantity_cannot_exceed_the_service_maximum(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[
            {
                "service_id": kp_setup.service_id,
                "included_quantity": MAX_QUANTITY_PER_BOOKING + 1,
            }
        ],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_included_exceeds_max"


async def test_service_maximum_cannot_drop_below_an_included_quantity(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[
            {
                "service_id": kp_setup.service_id,
                "included_quantity": MAX_QUANTITY_PER_BOOKING,
            }
        ],
    )

    response = await client.patch(
        f"/api/kp/services/{kp_setup.service_id}",
        json={"max_quantity_per_booking": MAX_QUANTITY_PER_BOOKING - 1},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_included_exceeds_max"


async def test_service_maximum_is_capped_at_the_global_ceiling(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await create_service(
        client,
        staff_headers,
        kp_setup.event_id,
        max_quantity_per_booking=MAX_SERVICE_QUANTITY + 1,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "validation.out_of_range"
    assert response.json()["fieldErrors"][0]["field"] == "max_quantity_per_booking"


async def test_booked_quantity_is_capped_at_the_global_ceiling(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await complete_company_profile(company_headers)

    response = await register_in_zone(
        client,
        company_headers,
        kp_setup.event_id,
        kp_setup.booth_zone_id,
        [
            {
                "service_id": kp_setup.service_id,
                "quantity": MAX_SERVICE_QUANTITY + 1,
            }
        ],
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "validation.out_of_range"


async def test_included_quantity_is_capped_at_the_global_ceiling(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[
            {
                "service_id": kp_setup.service_id,
                "included_quantity": MAX_SERVICE_QUANTITY + 1,
            }
        ],
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "validation.out_of_range"


async def test_event_exposes_its_nametag_limit(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}", headers=staff_headers
    )

    assert response.status_code == 200
    assert response.json()["max_nametags_per_booking"] == 10


async def test_nametag_limit_can_be_configured(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.patch(
        f"/api/kp/events/{kp_setup.event_id}",
        json={"max_nametags_per_booking": 4},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["max_nametags_per_booking"] == 4


async def test_nametag_limit_must_be_at_least_one(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.patch(
        f"/api/kp/events/{kp_setup.event_id}",
        json={"max_nametags_per_booking": 0},
        headers=staff_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "validation.out_of_range"


async def test_zone_layout_description_is_stored(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    zone = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        layout_description=LAYOUT_DESCRIPTION,
    )

    response = await client.patch(
        f"/api/kp/booth-zones/{zone.json()['id']}",
        json={"layout_description": "One table only."},
        headers=staff_headers,
    )

    assert zone.json()["layout_description"] == LAYOUT_DESCRIPTION
    assert response.status_code == 200
    assert response.json()["layout_description"] == "One table only."


async def test_zone_layout_description_is_limited_in_length(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        layout_description="x" * 2001,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "validation.too_long"


async def test_zone_layout_url_is_visible_to_staff_and_to_every_company(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    other_company_headers: dict[str, str],
    kp_setup: KpSetup,
):
    await client.put(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}/layout-file",
        files={"file": ("layout.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        headers=staff_headers,
    )

    staff_zones = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones", headers=staff_headers
    )
    company_zones = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones/available",
        headers=company_headers,
    )
    other_company_zones = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones/available",
        headers=other_company_headers,
    )

    assert [zone["layout_url"] for zone in staff_zones.json()] == [
        "https://storage.test/download"
    ]
    assert [zone["layout_url"] for zone in company_zones.json()] == [
        "https://storage.test/download"
    ]
    assert [zone["layout_url"] for zone in other_company_zones.json()] == [
        "https://storage.test/download"
    ]


async def test_zones_embedded_in_bookings_carry_the_layout_url(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = (await register_booking(company_headers, kp_setup)).json()
    upgrade_zone = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        name="Gold",
        color="#AABBCC",
        capacity=0,
    )
    upgrade_zone_id = upgrade_zone.json()["id"]
    for zone_id in (kp_setup.booth_zone_id, upgrade_zone_id):
        await client.put(
            f"/api/kp/booth-zones/{zone_id}/layout-file",
            files={"file": ("layout.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            headers=staff_headers,
        )
    await client.put(
        f"/api/kp/bookings/{booking['id']}/upgrade-waitlist",
        json={"target_booth_zone_ids": [upgrade_zone_id]},
        headers=company_headers,
    )

    my_booking = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/my-booking", headers=company_headers
    )
    staff_booking = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{booking['id']}",
        headers=staff_headers,
    )
    waitlist = await client.get(
        f"/api/kp/bookings/{booking['id']}/upgrade-waitlist", headers=company_headers
    )

    assert (
        my_booking.json()["booth_zone"]["layout_url"] == "https://storage.test/download"
    )
    assert (
        staff_booking.json()["booth_zone"]["layout_url"]
        == "https://storage.test/download"
    )
    assert [entry["target_booth_zone"]["layout_url"] for entry in waitlist.json()] == [
        "https://storage.test/download"
    ]


async def test_zone_without_a_layout_file_has_no_layout_url(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones", headers=staff_headers
    )

    assert response.status_code == 200
    assert [zone["layout_url"] for zone in response.json()] == [None]


async def test_staff_zone_change_applies_the_new_zone_inclusions(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = (await register_booking(company_headers, kp_setup, quantity=1)).json()
    target = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        base_price=20000,
        included_services=[
            {
                "service_id": kp_setup.service_id,
                "included_quantity": MAX_QUANTITY_PER_BOOKING,
            }
        ],
    )

    response = await client.patch(
        f"/api/kp/bookings/{booking['id']}",
        json={"booth_zone_id": target.json()["id"]},
        headers=staff_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert [
        (service["quantity"], service["included_quantity"], service["charged_quantity"])
        for service in body["services"]
    ] == [(MAX_QUANTITY_PER_BOOKING, MAX_QUANTITY_PER_BOOKING, 0)]
    assert body["net_total"] == 20000


async def test_staff_zone_change_books_a_service_the_new_zone_includes(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = (await register_booking(company_headers, kp_setup, quantity=1)).json()
    element = await create_service(
        client,
        staff_headers,
        kp_setup.event_id,
        category=BOOTH_ELEMENT,
        price=3000,
        max_quantity_per_booking=4,
    )
    target = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        included_services=[
            {"service_id": element.json()["id"], "included_quantity": 3}
        ],
    )

    response = await client.patch(
        f"/api/kp/bookings/{booking['id']}",
        json={"booth_zone_id": target.json()["id"]},
        headers=staff_headers,
    )

    assert response.status_code == 200
    included = {
        service["service_id"]: (
            service["quantity"],
            service["included_quantity"],
        )
        for service in response.json()["services"]
    }
    assert included[element.json()["id"]] == (3, 3)


async def test_staff_zone_change_drops_the_previous_zone_inclusions(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    included_zone = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        base_price=20000,
        included_services=[
            {
                "service_id": kp_setup.service_id,
                "included_quantity": MAX_QUANTITY_PER_BOOKING,
            }
        ],
    )
    await complete_company_profile(company_headers)
    booking = await register_in_zone(
        client,
        company_headers,
        kp_setup.event_id,
        included_zone.json()["id"],
        [{"service_id": kp_setup.service_id, "quantity": 1}],
    )

    response = await client.patch(
        f"/api/kp/bookings/{booking.json()['id']}",
        json={"booth_zone_id": kp_setup.booth_zone_id},
        headers=staff_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert [
        (service["quantity"], service["included_quantity"], service["charged_quantity"])
        for service in body["services"]
    ] == [(MAX_QUANTITY_PER_BOOKING, 0, MAX_QUANTITY_PER_BOOKING)]
    assert body["net_total"] == 10000 + MAX_QUANTITY_PER_BOOKING * 5000
