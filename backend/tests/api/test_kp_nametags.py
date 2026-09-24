from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.kp_event import KpEvent
from tests.api.conftest import KpSetup

ADA = {"first_name": "Ada", "last_name": "Lovelace", "position": "Engineer"}
GRACE = {"first_name": "Grace", "last_name": "Hopper", "position": "Admiral"}
ALAN = {"first_name": "Alan", "last_name": "Turing", "position": "Researcher"}


def people(payload: Any) -> list[tuple[str, str, str]]:
    return [
        (tag["first_name"], tag["last_name"], tag["position"]) for tag in payload.json()
    ]


async def put_nametags(
    client: AsyncClient,
    headers: dict[str, str],
    booking_id: str,
    name_tags: list[dict[str, str]],
) -> Response:
    return await client.put(
        f"/api/kp/bookings/{booking_id}/nametags",
        json={"name_tags": name_tags},
        headers=headers,
    )


async def get_nametags(
    client: AsyncClient, headers: dict[str, str], booking_id: str
) -> Response:
    return await client.get(f"/api/kp/bookings/{booking_id}/nametags", headers=headers)


async def pass_nametags_deadline(db_session: AsyncSession, event_id: str) -> None:
    statement = select(KpEvent).where(col(KpEvent.id) == UUID(event_id))
    event = (await db_session.execute(statement)).scalar_one()
    today = date.today()
    event.registration_open = today - timedelta(days=40)
    event.registration_end = today - timedelta(days=30)
    event.nametags_deadline = today - timedelta(days=1)
    db_session.add(event)
    await db_session.commit()


async def set_nametag_cap(
    client: AsyncClient, staff_headers: dict[str, str], event_id: str, cap: int
) -> Response:
    return await client.patch(
        f"/api/kp/events/{event_id}",
        json={"max_nametags_per_booking": cap},
        headers=staff_headers,
    )


@pytest.fixture
async def booking_id(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
) -> str:
    return (await register_booking(company_headers, kp_setup)).json()["id"]


async def test_a_fresh_booking_has_no_nametags(
    client: AsyncClient, company_headers: dict[str, str], booking_id: str
):
    response = await get_nametags(client, company_headers, booking_id)

    assert response.status_code == 200
    assert response.json() == []


async def test_put_stores_the_nametags_sorted_by_name(
    client: AsyncClient, company_headers: dict[str, str], booking_id: str
):
    response = await put_nametags(client, company_headers, booking_id, [GRACE, ADA])
    stored = await get_nametags(client, company_headers, booking_id)

    assert response.status_code == 200
    assert people(response) == [
        ("Grace", "Hopper", "Admiral"),
        ("Ada", "Lovelace", "Engineer"),
    ]
    assert people(stored) == people(response)
    assert all(tag["booking_id"] == booking_id for tag in stored.json())


async def test_put_replaces_the_previous_list(
    client: AsyncClient, company_headers: dict[str, str], booking_id: str
):
    await put_nametags(client, company_headers, booking_id, [ADA, GRACE])

    response = await put_nametags(client, company_headers, booking_id, [ALAN])

    assert people(response) == [("Alan", "Turing", "Researcher")]
    assert people(await get_nametags(client, company_headers, booking_id)) == [
        ("Alan", "Turing", "Researcher")
    ]


async def test_an_empty_list_clears_the_nametags(
    client: AsyncClient, company_headers: dict[str, str], booking_id: str
):
    await put_nametags(client, company_headers, booking_id, [ADA])

    response = await put_nametags(client, company_headers, booking_id, [])

    assert response.json() == []


async def test_more_nametags_than_the_event_allows_are_refused(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    await set_nametag_cap(client, staff_headers, kp_setup.event_id, 2)
    await put_nametags(client, company_headers, booking_id, [ADA, GRACE])

    response = await put_nametags(
        client, company_headers, booking_id, [ADA, GRACE, ALAN]
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_nametag_limit_reached"
    assert people(await get_nametags(client, company_headers, booking_id)) == [
        ("Grace", "Hopper", "Admiral"),
        ("Ada", "Lovelace", "Engineer"),
    ]


async def test_exactly_the_allowed_number_of_nametags_is_accepted(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    await set_nametag_cap(client, staff_headers, kp_setup.event_id, 2)

    response = await put_nametags(client, company_headers, booking_id, [ADA, GRACE])

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_nametags_are_refused_after_the_nametags_deadline(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    await put_nametags(client, company_headers, booking_id, [ADA])
    await pass_nametags_deadline(db_session, kp_setup.event_id)

    response = await put_nametags(client, company_headers, booking_id, [GRACE])

    assert response.status_code == 403
    assert response.json()["code"] == "error.kp_nametags_deadline_passed"
    assert people(await get_nametags(client, company_headers, booking_id)) == [
        ("Ada", "Lovelace", "Engineer")
    ]


async def test_reading_nametags_stays_open_after_the_deadline(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    await put_nametags(client, company_headers, booking_id, [ADA])
    await pass_nametags_deadline(db_session, kp_setup.event_id)

    response = await get_nametags(client, company_headers, booking_id)

    assert response.status_code == 200
    assert people(response) == [("Ada", "Lovelace", "Engineer")]


async def test_nametags_can_still_be_edited_after_confirmation(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    booking_id: str,
):
    await client.post(f"/api/kp/bookings/{booking_id}/accept", headers=staff_headers)

    response = await put_nametags(client, company_headers, booking_id, [ADA])

    assert response.status_code == 200
    assert people(response) == [("Ada", "Lovelace", "Engineer")]


async def test_nametags_of_a_cancelled_booking_are_read_only(
    client: AsyncClient, company_headers: dict[str, str], booking_id: str
):
    await client.patch(
        f"/api/kp/bookings/{booking_id}/status",
        json={"status": "CANCELLED"},
        headers=company_headers,
    )

    response = await put_nametags(client, company_headers, booking_id, [ADA])

    assert response.status_code == 403
    assert response.json()["code"] == "error.kp_booking_readonly"


async def test_nametags_do_not_belong_to_the_missing_items(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/my-booking", headers=company_headers
    )

    assert response.json()["missing_items"] == []
    assert response.json()["is_complete"] is True


async def test_staff_can_read_the_nametags_of_any_booking(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    booking_id: str,
):
    await put_nametags(client, company_headers, booking_id, [ADA])

    response = await client.get(
        f"/api/kp/staff/bookings/{booking_id}/nametags", headers=staff_headers
    )

    assert response.status_code == 200
    assert people(response) == [("Ada", "Lovelace", "Engineer")]


async def test_a_company_cannot_use_the_staff_read(
    client: AsyncClient, company_headers: dict[str, str], booking_id: str
):
    response = await client.get(
        f"/api/kp/staff/bookings/{booking_id}/nametags", headers=company_headers
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_nametags_of_an_unknown_booking_are_not_found(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await get_nametags(
        client, company_headers, "00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.kp_booking_not_found"


async def test_the_nametag_count_of_the_staff_booking_follows_the_list(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    await put_nametags(client, company_headers, booking_id, [ADA, GRACE])

    response = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{booking_id}",
        headers=staff_headers,
    )

    assert response.json()["nametag_count"] == 2
