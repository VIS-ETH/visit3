from httpx import AsyncClient

from tests.api.conftest import KpSetup


async def test_duplicate_booth_zone_name_conflicts(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Main hall", "color": "#112233"},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_zone_name_exists"


async def test_duplicate_booth_zone_color_conflicts(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Side hall", "color": "#000000"},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_zone_color_exists"


async def test_renaming_booth_zone_onto_another_name_conflicts(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    other = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Side hall", "color": "#112233"},
        headers=staff_headers,
    )

    response = await client.patch(
        f"/api/kp/booth-zones/{other.json()['id']}",
        json={"name": "Main hall"},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_zone_name_exists"


async def test_recoloring_booth_zone_onto_another_color_conflicts(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    other = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Side hall", "color": "#112233"},
        headers=staff_headers,
    )

    response = await client.patch(
        f"/api/kp/booth-zones/{other.json()['id']}",
        json={"color": "#000000"},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_zone_color_exists"


async def test_booth_zone_keeps_its_own_name_and_color_on_update(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.patch(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}",
        json={"name": "Main hall", "color": "#000000", "capacity": 9},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["capacity"] == 9


async def test_booth_zone_name_and_color_are_reusable_after_deletion(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    deleted = await client.delete(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}", headers=staff_headers
    )

    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Main hall", "color": "#000000"},
        headers=staff_headers,
    )

    assert deleted.status_code == 200
    assert response.status_code == 200
    assert response.json()["id"] != kp_setup.booth_zone_id


async def test_duplicate_service_name_conflicts(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={"name": "Electricity"},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_service_name_exists"


async def test_renaming_service_onto_another_name_conflicts(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    other = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={"name": "Carpet"},
        headers=staff_headers,
    )

    response = await client.patch(
        f"/api/kp/services/{other.json()['id']}",
        json={"name": "Electricity"},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_service_name_exists"


async def test_service_keeps_its_own_name_on_update(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.patch(
        f"/api/kp/services/{kp_setup.service_id}",
        json={"name": "Electricity", "price": 7000},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["price"] == 7000


async def test_service_name_is_reusable_after_deletion(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    deleted = await client.delete(
        f"/api/kp/services/{kp_setup.service_id}", headers=staff_headers
    )

    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={"name": "Electricity"},
        headers=staff_headers,
    )

    assert deleted.status_code == 200
    assert response.status_code == 200
    assert response.json()["id"] != kp_setup.service_id


async def test_same_names_are_allowed_in_another_event(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    other_event = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/clone",
        json={
            "name": "Kontaktparty clone",
            "registration_open": "2030-01-01",
            "registration_end": "2030-01-10",
            "finalization_deadline": "2030-01-11",
            "nametags_deadline": "2030-01-12",
            "event_date": "2030-02-01",
        },
        headers=staff_headers,
    )

    assert other_event.status_code == 200
    zones = await client.get(
        f"/api/kp/events/{other_event.json()['id']}/booth-zones",
        headers=staff_headers,
    )
    assert [zone["name"] for zone in zones.json()] == ["Main hall"]
