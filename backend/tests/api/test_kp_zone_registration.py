from collections.abc import Awaitable, Callable
from datetime import timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dates import local_today
from app.models.kp_event import KpEventRegistrationException
from app.models.user import User
from tests.api.conftest import KpSetup

CLOSED_CODE = "error.kp_zone_registration_closed"


async def create_zone(
    client: AsyncClient, staff_headers: dict[str, str], event_id: str
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": "Gold", "color": "#AABBCC", "capacity": 3},
        headers=staff_headers,
    )
    return response.json()["id"]


async def set_zone_open(
    client: AsyncClient, headers: dict[str, str], zone_id: str, is_open: bool
) -> Response:
    return await client.patch(
        f"/api/kp/booth-zones/{zone_id}",
        json={"registration_open": is_open},
        headers=headers,
    )


async def register_into(
    client: AsyncClient,
    complete_company_profile: Callable[..., Awaitable[Response]],
    headers: dict[str, str],
    event_id: str,
    zone_id: str,
) -> Response:
    await complete_company_profile(headers)
    return await client.post(
        f"/api/kp/events/{event_id}/bookings/register",
        json={"booth_zone_id": zone_id, "confirm_profile": True},
        headers=headers,
    )


async def company_zone_flags(
    client: AsyncClient, headers: dict[str, str], event_id: str
) -> dict[str, bool]:
    response = await client.get(
        f"/api/kp/events/{event_id}/booth-zones/available", headers=headers
    )
    return {zone["id"]: zone["registration_open"] for zone in response.json()}


async def grant_exception(
    db_session: AsyncSession, event_id: str, company_user: User, days: int
) -> None:
    assert company_user.company_id is not None
    db_session.add(
        KpEventRegistrationException(
            event_id=UUID(event_id),
            company_id=company_user.company_id,
            allowed_until=local_today() + timedelta(days=days),
        )
    )
    await db_session.commit()


async def test_zones_are_open_by_default(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
):
    staff_zones = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones", headers=staff_headers
    )

    assert staff_zones.json()[0]["registration_open"] is True
    assert await company_zone_flags(client, company_headers, kp_setup.event_id) == {
        kp_setup.booth_zone_id: True
    }


async def test_staff_can_close_and_reopen_a_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
):
    closed = await set_zone_open(client, staff_headers, kp_setup.booth_zone_id, False)

    assert closed.status_code == 200
    assert closed.json()["registration_open"] is False
    assert await company_zone_flags(client, company_headers, kp_setup.event_id) == {
        kp_setup.booth_zone_id: False
    }

    reopened = await set_zone_open(client, staff_headers, kp_setup.booth_zone_id, True)

    assert reopened.json()["registration_open"] is True


async def test_registering_into_a_closed_zone_is_refused(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await set_zone_open(client, staff_headers, kp_setup.booth_zone_id, False)

    response = await register_into(
        client,
        complete_company_profile,
        company_headers,
        kp_setup.event_id,
        kp_setup.booth_zone_id,
    )

    assert response.status_code == 403
    assert response.json()["code"] == CLOSED_CODE


async def test_registering_into_an_open_zone_next_to_a_closed_one_works(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    open_zone_id = await create_zone(client, staff_headers, kp_setup.event_id)
    await set_zone_open(client, staff_headers, kp_setup.booth_zone_id, False)

    response = await register_into(
        client,
        complete_company_profile,
        company_headers,
        kp_setup.event_id,
        open_zone_id,
    )

    assert response.status_code == 200
    assert response.json()["booth_zone_id"] == open_zone_id


async def test_a_registration_exception_overrides_a_closed_zone(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await set_zone_open(client, staff_headers, kp_setup.booth_zone_id, False)
    await grant_exception(db_session, kp_setup.event_id, company_user, 1)

    flags = await company_zone_flags(client, company_headers, kp_setup.event_id)
    response = await register_into(
        client,
        complete_company_profile,
        company_headers,
        kp_setup.event_id,
        kp_setup.booth_zone_id,
    )

    assert flags == {kp_setup.booth_zone_id: True}
    assert response.status_code == 200


async def test_an_expired_registration_exception_keeps_the_zone_closed(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    await set_zone_open(client, staff_headers, kp_setup.booth_zone_id, False)
    await grant_exception(db_session, kp_setup.event_id, company_user, -1)

    response = await register_into(
        client,
        complete_company_profile,
        company_headers,
        kp_setup.event_id,
        kp_setup.booth_zone_id,
    )

    assert response.status_code == 403
    assert response.json()["code"] == CLOSED_CODE


@pytest.fixture
async def booking_id(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> str:
    response = await register_into(
        client,
        complete_company_profile,
        company_headers,
        kp_setup.event_id,
        kp_setup.booth_zone_id,
    )
    return response.json()["id"]


async def test_switching_into_a_closed_zone_is_refused(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    target_id = await create_zone(client, staff_headers, kp_setup.event_id)
    await set_zone_open(client, staff_headers, target_id, False)

    response = await client.post(
        f"/api/kp/bookings/{booking_id}/switch-zone",
        json={"booth_zone_id": target_id},
        headers=company_headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == CLOSED_CODE


async def test_a_booking_in_a_closed_zone_can_still_switch_out(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    target_id = await create_zone(client, staff_headers, kp_setup.event_id)
    await set_zone_open(client, staff_headers, kp_setup.booth_zone_id, False)

    response = await client.post(
        f"/api/kp/bookings/{booking_id}/switch-zone",
        json={"booth_zone_id": target_id},
        headers=company_headers,
    )

    assert response.status_code == 200
    assert response.json()["booth_zone_id"] == target_id


async def test_a_booking_in_a_closed_zone_stays_editable(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    await set_zone_open(client, staff_headers, kp_setup.booth_zone_id, False)

    response = await client.post(
        f"/api/kp/bookings/{booking_id}/services",
        json={"services": [{"service_id": kp_setup.service_id, "quantity": 1}]},
        headers=company_headers,
    )

    assert response.status_code == 200
    assert response.json()["booth_zone_id"] == kp_setup.booth_zone_id


async def test_joining_the_waitlist_of_a_closed_zone_is_refused(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    booking_id: str,
):
    full_zone = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Full", "color": "#010203", "capacity": 0},
        headers=staff_headers,
    )
    full_zone_id = full_zone.json()["id"]
    await set_zone_open(client, staff_headers, full_zone_id, False)

    response = await client.put(
        f"/api/kp/bookings/{booking_id}/upgrade-waitlist",
        json={"target_booth_zone_ids": [full_zone_id]},
        headers=company_headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == CLOSED_CODE


async def test_companies_cannot_toggle_a_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
):
    response = await set_zone_open(
        client, company_headers, kp_setup.booth_zone_id, False
    )

    assert response.status_code == 403
    assert await company_zone_flags(client, company_headers, kp_setup.event_id) == {
        kp_setup.booth_zone_id: True
    }


async def test_staff_without_president_role_cannot_toggle_a_zone(
    client: AsyncClient,
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    kp_setup: KpSetup,
):
    headers = {**await auth_headers(staff_user), **csrf_headers}

    response = await set_zone_open(client, headers, kp_setup.booth_zone_id, False)

    assert response.status_code == 403
