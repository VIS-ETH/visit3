from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from httpx import AsyncClient, Response

from tests.api.conftest import KpSetup, kp_payload


async def create_service(
    client: AsyncClient,
    staff_headers: dict[str, str],
    event_id: str,
    name: str,
    **overrides: Any,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/kp/events/{event_id}/services",
        json={"name": name, **overrides},
        headers=staff_headers,
    )
    assert response.status_code == 200, response.json()
    return response.json()


async def register(
    client: AsyncClient,
    headers: dict[str, str],
    kp_setup: KpSetup,
    services: list[dict[str, Any]],
) -> Response:
    return await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={
            "booth_zone_id": kp_setup.booth_zone_id,
            "services": services,
            "confirm_profile": True,
        },
        headers=headers,
    )


def lines(booking: dict[str, Any]) -> dict[str, tuple[int, int, int]]:
    return {
        service["service"]["name"]: (
            service["quantity"],
            service["included_quantity"],
            service["charged_quantity"],
        )
        for service in booking["services"]
    }


@pytest.fixture
async def tables(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
) -> dict[str, dict[str, Any]]:
    normal = await create_service(
        client, staff_headers, kp_setup.event_id, "Normal table", price=3000
    )
    no_normal = await create_service(
        client,
        staff_headers,
        kp_setup.event_id,
        "No normal table",
        excluded_service_ids=[normal["id"]],
    )
    standing = await create_service(
        client,
        staff_headers,
        kp_setup.event_id,
        "Standing table",
        price=4000,
        included_services=[{"service_id": no_normal["id"], "included_quantity": 1}],
    )
    return {"normal": normal, "no_normal": no_normal, "standing": standing}


async def test_exclusions_are_listed_on_both_services(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/services", headers=staff_headers
    )

    by_name = {service["name"]: service for service in response.json()}
    assert by_name["Normal table"]["excluded_service_ids"] == [
        tables["no_normal"]["id"]
    ]
    assert by_name["No normal table"]["excluded_service_ids"] == [
        tables["normal"]["id"]
    ]
    assert by_name["Standing table"]["included_services"] == [
        {"service_id": tables["no_normal"]["id"], "included_quantity": 1}
    ]


async def test_clearing_exclusions_removes_both_directions(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    await client.patch(
        f"/api/kp/services/{tables['normal']['id']}",
        json={"excluded_service_ids": []},
        headers=staff_headers,
    )

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/services", headers=staff_headers
    )

    assert all(service["excluded_service_ids"] == [] for service in response.json())


@pytest.mark.parametrize(
    ("relation", "code"),
    [
        ("self_include", "error.kp_service_relation_invalid"),
        ("self_exclude", "error.kp_service_relation_invalid"),
        ("nested_package", "error.kp_service_relation_invalid"),
        ("package_inside_package", "error.kp_service_relation_invalid"),
        ("include_and_exclude", "error.kp_service_relation_invalid"),
        ("contents_exclude_each_other", "error.kp_service_relation_invalid"),
        ("too_many", "error.kp_included_exceeds_max"),
        ("duplicate", "error.kp_included_service_duplicate"),
    ],
)
async def test_invalid_relations_are_refused(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
    relation: str,
    code: str,
):
    standing_id = tables["standing"]["id"]
    no_normal_id = tables["no_normal"]["id"]
    normal_id = tables["normal"]["id"]
    payloads: dict[str, tuple[str, dict[str, Any]]] = {
        "self_include": (
            normal_id,
            {"included_services": [{"service_id": normal_id}]},
        ),
        "self_exclude": (normal_id, {"excluded_service_ids": [normal_id]}),
        "nested_package": (
            kp_setup.service_id,
            {"included_services": [{"service_id": standing_id}]},
        ),
        "package_inside_package": (
            no_normal_id,
            {"included_services": [{"service_id": kp_setup.service_id}]},
        ),
        "include_and_exclude": (
            standing_id,
            {"excluded_service_ids": [no_normal_id]},
        ),
        "contents_exclude_each_other": (
            standing_id,
            {
                "included_services": [
                    {"service_id": no_normal_id},
                    {"service_id": normal_id},
                ]
            },
        ),
        "too_many": (
            standing_id,
            {"included_services": [{"service_id": normal_id, "included_quantity": 2}]},
        ),
        "duplicate": (
            standing_id,
            {
                "included_services": [
                    {"service_id": normal_id},
                    {"service_id": normal_id},
                ]
            },
        ),
    }
    service_id, payload = payloads[relation]

    response = await client.patch(
        f"/api/kp/services/{service_id}", json=payload, headers=staff_headers
    )

    assert response.status_code == 400
    assert response.json()["code"] == code


async def test_a_relation_to_another_event_is_refused(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    other_event = await client.post(
        "/api/kp/create", json=kp_payload("Other KP"), headers=staff_headers
    )
    foreign = await create_service(
        client, staff_headers, other_event.json()["id"], "Foreign table"
    )

    response = await client.patch(
        f"/api/kp/services/{tables['normal']['id']}",
        json={"excluded_service_ids": [foreign["id"]]},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_service_event_mismatch"


async def test_booking_a_package_books_its_contents_for_free(
    client: AsyncClient,
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    await complete_company_profile(company_headers)

    response = await register(
        client,
        company_headers,
        kp_setup,
        [{"service_id": tables["standing"]["id"], "quantity": 1}],
    )

    assert response.status_code == 200, response.json()
    assert lines(response.json()) == {
        "Standing table": (1, 0, 1),
        "No normal table": (1, 1, 0),
    }
    assert response.json()["net_total"] == 10000 + 4000


async def test_excluded_services_cannot_be_booked_together(
    client: AsyncClient,
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    await complete_company_profile(company_headers)

    response = await register(
        client,
        company_headers,
        kp_setup,
        [
            {"service_id": tables["standing"]["id"], "quantity": 1},
            {"service_id": tables["normal"]["id"], "quantity": 1},
        ],
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_services_excluded"


async def test_adding_an_excluded_service_later_is_refused(
    client: AsyncClient,
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    await complete_company_profile(company_headers)
    booking = await register(
        client,
        company_headers,
        kp_setup,
        [{"service_id": tables["normal"]["id"], "quantity": 1}],
    )

    response = await client.post(
        f"/api/kp/bookings/{booking.json()['id']}/services",
        json={"services": [{"service_id": tables["standing"]["id"], "quantity": 1}]},
        headers=company_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_services_excluded"


async def test_adding_a_package_later_books_its_contents_for_free(
    client: AsyncClient,
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    await complete_company_profile(company_headers)
    booking = await register(client, company_headers, kp_setup, [])

    response = await client.post(
        f"/api/kp/bookings/{booking.json()['id']}/services",
        json={"services": [{"service_id": tables["standing"]["id"], "quantity": 1}]},
        headers=company_headers,
    )

    assert response.status_code == 200, response.json()
    assert lines(response.json()) == {
        "Standing table": (1, 0, 1),
        "No normal table": (1, 1, 0),
    }


async def test_a_zone_switch_keeps_package_contents_free(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    await complete_company_profile(company_headers)
    booking = await register(
        client,
        company_headers,
        kp_setup,
        [{"service_id": tables["standing"]["id"], "quantity": 1}],
    )
    target = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Side hall", "color": "#ABCDEF", "capacity": 2},
        headers=staff_headers,
    )

    response = await client.patch(
        f"/api/kp/bookings/{booking.json()['id']}",
        json={"booth_zone_id": target.json()["id"]},
        headers=staff_headers,
    )

    assert response.status_code == 200, response.json()
    assert lines(response.json())["No normal table"] == (1, 1, 0)


async def test_deleting_a_service_drops_its_relations(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    deleted = await client.delete(
        f"/api/kp/services/{tables['no_normal']['id']}", headers=staff_headers
    )
    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/services", headers=staff_headers
    )

    assert deleted.status_code in (200, 204)
    by_name = {service["name"]: service for service in response.json()}
    assert by_name["Normal table"]["excluded_service_ids"] == []
    assert by_name["Standing table"]["included_services"] == []


async def test_cloning_an_event_keeps_the_relations(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    tables: dict[str, dict[str, Any]],
):
    clone = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/clone",
        json=kp_payload("Kontaktparty clone"),
        headers=staff_headers,
    )
    response = await client.get(
        f"/api/kp/events/{clone.json()['id']}/services", headers=staff_headers
    )

    by_name = {service["name"]: service for service in response.json()}
    assert by_name["Normal table"]["excluded_service_ids"] == [
        by_name["No normal table"]["id"]
    ]
    assert by_name["Standing table"]["included_services"] == [
        {"service_id": by_name["No normal table"]["id"], "included_quantity": 1}
    ]
