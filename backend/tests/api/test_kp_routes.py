from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock
from uuid import UUID

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kp_event import KpEventBoothZoneServiceLink
from app.models.user import User
from tests.api.conftest import (
    MAX_QUANTITY_PER_BOOKING,
    PNG_BYTES,
    PNG_UPLOAD,
    KpSetup,
    kp_payload,
    move_event_into_the_past,
)


async def test_staff_creates_event_with_booth_zone_and_service(
    client: AsyncClient, staff_headers: dict[str, str]
):
    payload = kp_payload("Kontaktparty 2026")

    event = await client.post("/api/kp/create", json=payload, headers=staff_headers)

    assert event.status_code == 200
    event_id = event.json()["id"]
    assert event.json()["name"] == payload["name"]

    booth_zone = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": "Main hall", "capacity": 5},
        headers=staff_headers,
    )

    assert booth_zone.status_code == 200
    assert booth_zone.json()["event_id"] == event_id
    assert booth_zone.json()["capacity"] == 5

    service = await client.post(
        f"/api/kp/events/{event_id}/services",
        json={"name": "Electricity", "price": 5000},
        headers=staff_headers,
    )

    assert service.status_code == 200
    assert service.json()["event_id"] == event_id
    assert service.json()["is_active"] is True


async def test_staff_without_president_role_cannot_create_event(
    client: AsyncClient,
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    headers = {**await auth_headers(staff_user), **csrf_headers}

    response = await client.post("/api/kp/create", json=kp_payload(), headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_company_registers_booking(
    company_user: User,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    response = await register_booking(company_headers, kp_setup)

    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == kp_setup.event_id
    assert body["booth_zone_id"] == kp_setup.booth_zone_id
    assert body["company_id"] == str(company_user.company_id)
    assert body["status"] == "REGISTERED"
    assert [service["service_id"] for service in body["services"]] == [
        kp_setup.service_id
    ]
    assert body["net_total"] == 15000


async def test_second_booking_for_same_event_conflicts(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    response = await register_booking(company_headers, kp_setup)

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booking_already_exists"


async def test_quantity_above_service_maximum_is_rejected(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    response = await register_booking(
        company_headers, kp_setup, quantity=MAX_QUANTITY_PER_BOOKING + 1
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "error.kp_service_quantity_invalid"
    assert body["identifier"].startswith("booking_service:service_max_per_booking:")


async def include_service_in_zone(
    db_session: AsyncSession, kp_setup: KpSetup, included_quantity: int
) -> None:
    db_session.add(
        KpEventBoothZoneServiceLink(
            booth_zone_id=UUID(kp_setup.booth_zone_id),
            service_id=UUID(kp_setup.service_id),
            included_quantity=included_quantity,
        )
    )
    await db_session.commit()


async def test_booth_zone_listings_expose_included_services(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    db_session: AsyncSession,
):
    await include_service_in_zone(db_session, kp_setup, included_quantity=2)
    expected = [{"service_id": kp_setup.service_id, "included_quantity": 2}]

    staff_zones = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones", headers=staff_headers
    )
    company_zones = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones/available",
        headers=company_headers,
    )

    assert staff_zones.status_code == 200
    assert [zone["included_services"] for zone in staff_zones.json()] == [expected]
    assert company_zones.status_code == 200
    assert [zone["included_services"] for zone in company_zones.json()] == [expected]


async def test_booth_zone_without_inclusions_exposes_an_empty_list(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones", headers=staff_headers
    )

    assert response.status_code == 200
    assert [zone["included_services"] for zone in response.json()] == [[]]


async def test_available_services_expose_remaining_total_quantity(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    limited = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={
            "name": "Fridge",
            "price": 2000,
            "max_quantity_per_booking": 3,
            "max_total_quantity": 5,
        },
        headers=staff_headers,
    )
    limited_id = limited.json()["id"]
    await complete_company_profile(company_headers)
    booking = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={
            "booth_zone_id": kp_setup.booth_zone_id,
            "services": [{"service_id": limited_id, "quantity": 2}],
            "confirm_profile": True,
        },
        headers=company_headers,
    )
    assert booking.status_code == 200

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/services/available",
        headers=company_headers,
    )

    assert response.status_code == 200
    remaining = {
        service["id"]: service["remaining_total_quantity"]
        for service in response.json()
    }
    assert remaining[limited_id] == 3
    assert remaining[kp_setup.service_id] is None


async def test_included_service_quantity_is_free_part_of_total(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    db_session: AsyncSession,
    register_booking: Callable[..., Awaitable[Response]],
):
    await include_service_in_zone(db_session, kp_setup, included_quantity=2)

    response = await register_booking(company_headers, kp_setup, quantity=1)

    assert response.status_code == 200
    body = response.json()
    assert [
        (service["quantity"], service["included_quantity"])
        for service in body["services"]
    ] == [(2, 2)]
    assert body["additional_service_charges"] == []
    assert body["net_total"] == 10000


async def test_included_service_quantity_only_charges_the_extra_units(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    db_session: AsyncSession,
    register_booking: Callable[..., Awaitable[Response]],
):
    await include_service_in_zone(db_session, kp_setup, included_quantity=1)

    response = await register_booking(company_headers, kp_setup, quantity=2)

    assert response.status_code == 200
    body = response.json()
    assert [
        (service["quantity"], service["included_quantity"])
        for service in body["services"]
    ] == [(2, 1)]
    assert [
        (charge["quantity"], charge["charged_quantity"])
        for charge in body["additional_service_charges"]
    ] == [(2, 1)]
    assert body["net_total"] == 15000


async def test_deleting_booth_zone_with_active_booking_conflicts(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    response = await client.delete(
        f"/api/kp/booth-zones/{kp_setup.booth_zone_id}", headers=staff_headers
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_zone_in_use"


async def test_updating_service_returns_the_new_requirements(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
):
    requirement = {
        "type": "text",
        "name": "Power plug",
        "description": "Tell us which plug type your booth needs.",
        "order": 10,
    }

    response = await client.patch(
        f"/api/kp/services/{kp_setup.service_id}",
        json={"requirements": [requirement]},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["requirements"]] == [
        requirement["name"]
    ]

    reloaded = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/services", headers=staff_headers
    )
    stored = next(item for item in reloaded.json() if item["id"] == kp_setup.service_id)
    assert [item["name"] for item in stored["requirements"]] == [requirement["name"]]


async def test_deleting_service_booked_by_active_booking_conflicts(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    await register_booking(company_headers, kp_setup)

    response = await client.delete(
        f"/api/kp/services/{kp_setup.service_id}", headers=staff_headers
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_service_in_use"


async def test_company_can_register_again_after_cancelling(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    first = await register_booking(company_headers, kp_setup)
    booking_id = first.json()["id"]

    cancelled = await client.patch(
        f"/api/kp/bookings/{booking_id}/status",
        json={"status": "CANCELLED"},
        headers=company_headers,
    )
    second = await register_booking(company_headers, kp_setup)

    assert cancelled.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] != booking_id


async def test_reusing_a_booth_number_in_the_same_zone_conflicts(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
):
    first = await register_booking(company_headers, kp_setup)
    other_user = await create_user(email="other@example.com", company_name="Other AG")
    other_headers = {**await auth_headers(other_user), **csrf_headers}
    second = await register_booking(other_headers, kp_setup)

    taken = await client.patch(
        f"/api/kp/bookings/{first.json()['id']}/booth-number",
        json={"booth_nr": 7},
        headers=staff_headers,
    )
    response = await client.patch(
        f"/api/kp/bookings/{second.json()['id']}/booth-number",
        json={"booth_nr": 7},
        headers=staff_headers,
    )

    assert taken.status_code == 200
    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_number_taken"


async def test_company_can_cancel_after_the_finalization_deadline(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)
    booking_id = booking.json()["id"]
    await move_event_into_the_past(db_session, kp_setup.event_id)

    unchanged = await client.patch(
        f"/api/kp/bookings/{booking_id}/status",
        json={"status": "REGISTERED"},
        headers=company_headers,
    )
    finalized = await client.patch(
        f"/api/kp/bookings/{booking_id}/status",
        json={"status": "FINALIZED"},
        headers=company_headers,
    )
    cancelled = await client.patch(
        f"/api/kp/bookings/{booking_id}/status",
        json={"status": "CANCELLED"},
        headers=company_headers,
    )

    assert unchanged.status_code == 200
    assert unchanged.json()["status"] == "REGISTERED"
    assert finalized.status_code == 403
    assert finalized.json()["code"] == "error.kp_finalization_deadline_passed"
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


async def test_upload_size_check_ignores_the_multipart_envelope(
    client: AsyncClient,
    storage_service: AsyncMock,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
):
    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/exports/nametags/background",
        files={"file": PNG_UPLOAD},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert storage_service.read_upload.await_args.kwargs["content_length"] == len(
        PNG_BYTES
    )
