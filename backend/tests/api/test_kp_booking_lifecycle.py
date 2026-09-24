from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZoneServiceLink,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
)
from app.models.user import User
from tests.api.conftest import (
    MAX_QUANTITY_PER_BOOKING,
    PNG_UPLOAD,
    KpSetup,
    move_event_into_the_past,
)

REJECTION_REASON = "Your booth zone is no longer available for this event."
OTHER_COMPANY_NAME = "Beta GmbH"
OTHER_COMPANY_EMAIL = "beta@example.com"
REQUIREMENT_DESCRIPTION = "Describe the booth layout in a few sentences."


@dataclass(frozen=True)
class BookingWorld:
    event_id: str
    booth_zone_id: str
    service_id: str
    booking_id: str
    company_headers: dict[str, str]
    staff_headers: dict[str, str]


async def drop_company_details(db_session: AsyncSession, booking_id: str) -> None:
    snapshot = (
        await db_session.execute(
            select(KpBookingCompanyDetails).where(
                col(KpBookingCompanyDetails.booking_id) == UUID(booking_id)
            )
        )
    ).scalar_one()
    await db_session.delete(snapshot)
    await db_session.commit()


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


@pytest.fixture
async def other_company_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email=OTHER_COMPANY_EMAIL, password=None, company_name=OTHER_COMPANY_NAME
    )


@pytest.fixture
async def other_company_headers(
    other_company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(other_company_user), **csrf_headers}


@pytest.fixture
async def booking_world(
    kp_setup: KpSetup,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
) -> BookingWorld:
    booking = (await register_booking(company_headers, kp_setup)).json()
    return BookingWorld(
        event_id=kp_setup.event_id,
        booth_zone_id=kp_setup.booth_zone_id,
        service_id=kp_setup.service_id,
        booking_id=booking["id"],
        company_headers=company_headers,
        staff_headers=staff_headers,
    )


async def test_my_booking_reports_completeness(
    client: AsyncClient, booking_world: BookingWorld
):
    response = await client.get(
        f"/api/kp/events/{booking_world.event_id}/my-booking",
        headers=booking_world.company_headers,
    )

    assert response.status_code == 200
    assert response.json()["missing_items"] == []
    assert response.json()["is_complete"] is True


async def test_completeness_survives_a_later_profile_edit(
    client: AsyncClient,
    booking_world: BookingWorld,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await complete_company_profile(booking_world.company_headers, billing_city="")

    response = await client.get(
        f"/api/kp/events/{booking_world.event_id}/my-booking",
        headers=booking_world.company_headers,
    )

    assert response.status_code == 200
    assert response.json()["missing_items"] == []
    assert response.json()["is_complete"] is True


async def test_my_booking_lists_the_missing_items(
    client: AsyncClient,
    db_session: AsyncSession,
    kp_setup: KpSetup,
    company_headers: dict[str, str],
    register_booking: Callable[..., Awaitable[Response]],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    requirement = KpEventServiceRequirement(
        service_id=UUID(kp_setup.service_id),
        type=KpEventServiceRequirementType.TEXT,
        name="Booth layout",
        description=REQUIREMENT_DESCRIPTION,
    )
    db_session.add(requirement)
    await db_session.commit()
    booking = (await register_booking(company_headers, kp_setup)).json()
    await drop_company_details(db_session, booking["id"])
    await complete_company_profile(company_headers, billing_city="")

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/my-booking", headers=company_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_complete"] is False
    assert f"requirement:{requirement.id}" in body["missing_items"]
    assert "company_profile" in body["missing_items"]
    assert "billing_address" in body["missing_items"]


async def test_staff_confirms_a_registered_booking(
    client: AsyncClient, booking_world: BookingWorld
):
    accepted = await client.post(
        f"/api/kp/bookings/{booking_world.booking_id}/accept",
        headers=booking_world.staff_headers,
    )

    assert accepted.status_code == 200
    assert accepted.json()["status"] == "CONFIRMED"
    assert accepted.json()["confirmed_at"] is not None


async def test_staff_undoes_an_acceptance(
    client: AsyncClient, booking_world: BookingWorld
):
    await client.post(
        f"/api/kp/bookings/{booking_world.booking_id}/accept",
        headers=booking_world.staff_headers,
    )

    response = await client.post(
        f"/api/kp/bookings/{booking_world.booking_id}/undo-accept",
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REGISTERED"
    assert response.json()["confirmed_at"] is None


async def test_reject_stores_the_reason_and_frees_capacity(
    client: AsyncClient,
    booking_world: BookingWorld,
    other_company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await client.patch(
        f"/api/kp/booth-zones/{booking_world.booth_zone_id}",
        json={"capacity": 1},
        headers=booking_world.staff_headers,
    )
    await complete_company_profile(other_company_headers)
    blocked = await client.post(
        f"/api/kp/events/{booking_world.event_id}/bookings/register",
        json={"booth_zone_id": booking_world.booth_zone_id, "confirm_profile": True},
        headers=other_company_headers,
    )

    assert blocked.status_code == 409
    assert blocked.json()["code"] == "error.kp_booth_zone_at_capacity"

    rejected = await client.post(
        f"/api/kp/bookings/{booking_world.booking_id}/reject",
        json={"reason": REJECTION_REASON},
        headers=booking_world.staff_headers,
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["rejection_reason"] == REJECTION_REASON

    retried = await client.post(
        f"/api/kp/events/{booking_world.event_id}/bookings/register",
        json={"booth_zone_id": booking_world.booth_zone_id, "confirm_profile": True},
        headers=other_company_headers,
    )

    assert retried.status_code == 200


@pytest.mark.parametrize("reason", ["too short", " " * 12])
async def test_reject_requires_a_real_reason(
    client: AsyncClient, booking_world: BookingWorld, reason: str
):
    response = await client.post(
        f"/api/kp/bookings/{booking_world.booking_id}/reject",
        json={"reason": reason},
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "error.validation_failed"


async def test_staff_edits_zone_booth_number_and_quantities(
    client: AsyncClient, booking_world: BookingWorld, staff_headers: dict[str, str]
):
    spare_zone = await client.post(
        f"/api/kp/events/{booking_world.event_id}/booth-zones",
        json={"name": "Side hall", "capacity": 2, "color": "#ABCDEF"},
        headers=staff_headers,
    )

    response = await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={
            "booth_zone_id": spare_zone.json()["id"],
            "booth_nr": 12,
            "status_note": "Moved on request",
            "services": [
                {"service_id": booking_world.service_id, "quantity": 2},
            ],
        },
        headers=staff_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["booth_zone_id"] == spare_zone.json()["id"]
    assert body["booth_nr"] == 12
    assert body["status_note"] == "Moved on request"
    assert [service["quantity"] for service in body["services"]] == [2]


async def test_staff_edit_removes_a_service_with_quantity_zero(
    client: AsyncClient, booking_world: BookingWorld
):
    response = await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={"services": [{"service_id": booking_world.service_id, "quantity": 0}]},
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["services"] == []


async def test_staff_edit_rejects_a_quantity_above_the_maximum(
    client: AsyncClient, booking_world: BookingWorld
):
    response = await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={
            "services": [
                {
                    "service_id": booking_world.service_id,
                    "quantity": MAX_QUANTITY_PER_BOOKING + 1,
                }
            ]
        },
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_service_quantity_invalid"


async def test_staff_edit_rejects_a_full_target_zone(
    client: AsyncClient,
    booking_world: BookingWorld,
    other_company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    full_zone = await client.post(
        f"/api/kp/events/{booking_world.event_id}/booth-zones",
        json={"name": "Tiny hall", "capacity": 1, "color": "#ABCDEF"},
        headers=booking_world.staff_headers,
    )
    await complete_company_profile(other_company_headers)
    await client.post(
        f"/api/kp/events/{booking_world.event_id}/bookings/register",
        json={"booth_zone_id": full_zone.json()["id"], "confirm_profile": True},
        headers=other_company_headers,
    )

    response = await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={"booth_zone_id": full_zone.json()["id"]},
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_zone_at_capacity"


async def test_staff_edit_rejects_a_taken_booth_number(
    client: AsyncClient,
    booking_world: BookingWorld,
    other_company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await complete_company_profile(other_company_headers)
    neighbour = await client.post(
        f"/api/kp/events/{booking_world.event_id}/bookings/register",
        json={"booth_zone_id": booking_world.booth_zone_id, "confirm_profile": True},
        headers=other_company_headers,
    )
    await client.patch(
        f"/api/kp/bookings/{neighbour.json()['id']}/booth-number",
        json={"booth_nr": 4},
        headers=booking_world.staff_headers,
    )

    response = await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={"booth_nr": 4},
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_number_taken"


async def test_staff_zone_change_clears_a_stale_booth_number(
    client: AsyncClient,
    booking_world: BookingWorld,
    other_company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    spare_zone = await client.post(
        f"/api/kp/events/{booking_world.event_id}/booth-zones",
        json={"name": "Side hall", "capacity": 2, "color": "#ABCDEF"},
        headers=booking_world.staff_headers,
    )
    spare_zone_id = spare_zone.json()["id"]
    await complete_company_profile(other_company_headers)
    neighbour = await client.post(
        f"/api/kp/events/{booking_world.event_id}/bookings/register",
        json={"booth_zone_id": spare_zone_id, "confirm_profile": True},
        headers=other_company_headers,
    )
    for booking_id in (neighbour.json()["id"], booking_world.booking_id):
        await client.patch(
            f"/api/kp/bookings/{booking_id}/booth-number",
            json={"booth_nr": 7},
            headers=booking_world.staff_headers,
        )

    response = await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={"booth_zone_id": spare_zone_id},
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["booth_zone_id"] == spare_zone_id
    assert response.json()["booth_nr"] is None


async def test_staff_zone_change_rejects_a_taken_booth_number(
    client: AsyncClient,
    booking_world: BookingWorld,
    other_company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    spare_zone = await client.post(
        f"/api/kp/events/{booking_world.event_id}/booth-zones",
        json={"name": "Side hall", "capacity": 2, "color": "#ABCDEF"},
        headers=booking_world.staff_headers,
    )
    spare_zone_id = spare_zone.json()["id"]
    await complete_company_profile(other_company_headers)
    neighbour = await client.post(
        f"/api/kp/events/{booking_world.event_id}/bookings/register",
        json={"booth_zone_id": spare_zone_id, "confirm_profile": True},
        headers=other_company_headers,
    )
    await client.patch(
        f"/api/kp/bookings/{neighbour.json()['id']}/booth-number",
        json={"booth_nr": 7},
        headers=booking_world.staff_headers,
    )

    response = await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={"booth_zone_id": spare_zone_id, "booth_nr": 7},
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booth_number_taken"


async def test_staff_zone_change_drops_the_waitlist_entry_of_the_target_zone(
    client: AsyncClient,
    booking_world: BookingWorld,
    db_session: AsyncSession,
):
    zones = [
        (
            await client.post(
                f"/api/kp/events/{booking_world.event_id}/booth-zones",
                json={"name": name, "capacity": 2, "color": color},
                headers=booking_world.staff_headers,
            )
        ).json()["id"]
        for name, color in (("Side hall", "#ABCDEF"), ("Back hall", "#FEDCBA"))
    ]
    for priority_rank, zone_id in enumerate(zones, 1):
        db_session.add(
            KpEventBookingUpgradeWaitlist(
                booking_id=UUID(booking_world.booking_id),
                target_booth_zone_id=UUID(zone_id),
                priority_rank=priority_rank,
            )
        )
    await db_session.commit()
    db_session.expunge_all()

    response = await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={"booth_zone_id": zones[0]},
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 200
    remaining = await client.get(
        f"/api/kp/bookings/{booking_world.booking_id}/upgrade-waitlist",
        headers=booking_world.company_headers,
    )
    assert [entry["target_booth_zone_id"] for entry in remaining.json()] == [zones[1]]


async def test_staff_zone_change_respects_the_service_stock(
    client: AsyncClient, booking_world: BookingWorld, db_session: AsyncSession
):
    generous_zone = await client.post(
        f"/api/kp/events/{booking_world.event_id}/booth-zones",
        json={"name": "Gold hall", "capacity": 2, "color": "#ABCDEF"},
        headers=booking_world.staff_headers,
    )
    spare_zone = await client.post(
        f"/api/kp/events/{booking_world.event_id}/booth-zones",
        json={"name": "Side hall", "capacity": 2, "color": "#FEDCBA"},
        headers=booking_world.staff_headers,
    )
    db_session.add(
        KpEventBoothZoneServiceLink(
            booth_zone_id=UUID(generous_zone.json()["id"]),
            service_id=UUID(booking_world.service_id),
            included_quantity=2,
        )
    )
    await db_session.commit()
    db_session.expunge_all()
    await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={"booth_zone_id": generous_zone.json()["id"]},
        headers=booking_world.staff_headers,
    )
    await client.patch(
        f"/api/kp/services/{booking_world.service_id}",
        json={"max_total_quantity": 1},
        headers=booking_world.staff_headers,
    )

    response = await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}",
        json={"booth_zone_id": spare_zone.json()["id"]},
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_service_quantity_invalid"


async def test_staff_deletes_a_registered_booking(
    client: AsyncClient, booking_world: BookingWorld
):
    response = await client.delete(
        f"/api/kp/bookings/{booking_world.booking_id}",
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 200

    booking = await client.get(
        f"/api/kp/events/{booking_world.event_id}/bookings/{booking_world.booking_id}",
        headers=booking_world.staff_headers,
    )

    assert booking.status_code == 404


async def test_a_confirmed_booking_is_only_deleted_with_force(
    client: AsyncClient, booking_world: BookingWorld
):
    await client.post(
        f"/api/kp/bookings/{booking_world.booking_id}/accept",
        headers=booking_world.staff_headers,
    )

    refused = await client.delete(
        f"/api/kp/bookings/{booking_world.booking_id}",
        headers=booking_world.staff_headers,
    )

    assert refused.status_code == 409
    assert refused.json()["code"] == "error.kp_booking_delete_requires_force"

    forced = await client.delete(
        f"/api/kp/bookings/{booking_world.booking_id}?force=true",
        headers=booking_world.staff_headers,
    )

    assert forced.status_code == 200


async def test_staff_booking_list_reports_completeness(
    client: AsyncClient, booking_world: BookingWorld
):
    response = await client.get(
        f"/api/kp/events/{booking_world.event_id}/bookings",
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 200
    assert [booking["is_complete"] for booking in response.json()] == [True]
    assert [booking["missing_items"] for booking in response.json()] == [[]]


async def test_staff_booking_list_presigns_each_stored_file_once(
    client: AsyncClient,
    booking_world: BookingWorld,
    company_headers_factory: Callable[[str], Awaitable[dict[str, str]]],
    complete_company_profile: Callable[..., Awaitable[Response]],
    storage_service: AsyncMock,
):
    await client.put(
        f"/api/kp/booth-zones/{booking_world.booth_zone_id}/layout-file",
        files={"file": PNG_UPLOAD},
        headers=booking_world.staff_headers,
    )
    await client.post(
        f"/api/kp/services/{booking_world.service_id}/image",
        files={"file": PNG_UPLOAD},
        headers=booking_world.staff_headers,
    )
    for name in ("first", "second", "third"):
        headers = await company_headers_factory(name)
        await complete_company_profile(headers)
        await client.post(
            f"/api/kp/events/{booking_world.event_id}/bookings/register",
            json={
                "booth_zone_id": booking_world.booth_zone_id,
                "services": [{"service_id": booking_world.service_id, "quantity": 1}],
                "confirm_profile": True,
            },
            headers=headers,
        )
    storage_service.generate_download_url.reset_mock()

    response = await client.get(
        f"/api/kp/events/{booking_world.event_id}/bookings",
        headers=booking_world.staff_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 4
    assert storage_service.generate_download_url.await_count == 2


async def test_my_booking_shows_the_rejected_booking_and_allows_registering(
    client: AsyncClient, booking_world: BookingWorld
):
    await client.post(
        f"/api/kp/bookings/{booking_world.booking_id}/reject",
        json={"reason": REJECTION_REASON},
        headers=booking_world.staff_headers,
    )

    response = await client.get(
        f"/api/kp/events/{booking_world.event_id}/my-booking",
        headers=booking_world.company_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == booking_world.booking_id
    assert response.json()["status"] == "REJECTED"
    assert response.json()["rejection_reason"] == REJECTION_REASON
    assert response.json()["can_register"] is True

    again = await client.post(
        f"/api/kp/events/{booking_world.event_id}/bookings/register",
        json={"booth_zone_id": booking_world.booth_zone_id, "confirm_profile": True},
        headers=booking_world.company_headers,
    )

    assert again.status_code == 200


async def test_my_booking_prefers_the_active_booking(
    client: AsyncClient, booking_world: BookingWorld
):
    response = await client.get(
        f"/api/kp/events/{booking_world.event_id}/my-booking",
        headers=booking_world.company_headers,
    )

    assert response.json()["status"] == "REGISTERED"
    assert response.json()["can_register"] is False


async def test_my_booking_cannot_register_after_the_registration_end(
    client: AsyncClient, db_session: AsyncSession, booking_world: BookingWorld
):
    await client.patch(
        f"/api/kp/bookings/{booking_world.booking_id}/status",
        json={"status": "CANCELLED"},
        headers=booking_world.company_headers,
    )
    await move_event_into_the_past(db_session, booking_world.event_id)

    response = await client.get(
        f"/api/kp/events/{booking_world.event_id}/my-booking",
        headers=booking_world.company_headers,
    )

    assert response.json()["status"] == "CANCELLED"
    assert response.json()["can_register"] is False
