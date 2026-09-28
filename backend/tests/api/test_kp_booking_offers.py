from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.dates import local_today
from app.models.kp_event import KpEvent, KpEventBooking
from app.models.user import User
from tests.api.conftest import KpSetup, decoded_subject

DEADLINE_PASSED_CODE = "error.kp_offer_cancel_deadline_passed"


async def create_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    event_id: str,
    *,
    name: str,
    color: str,
    capacity: int,
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": name, "color": color, "capacity": capacity},
        headers=staff_headers,
    )
    return response.json()["id"]


async def offer(
    client: AsyncClient,
    headers: dict[str, str],
    event_id: str,
    company_id: UUID | None,
    zone_id: str,
    cancel_until: date,
) -> Response:
    return await client.post(
        f"/api/kp/events/{event_id}/bookings/offer",
        json={
            "company_id": str(company_id),
            "booth_zone_id": zone_id,
            "cancel_until": cancel_until.isoformat(),
        },
        headers=headers,
    )


async def cancel(
    client: AsyncClient, headers: dict[str, str], booking_id: str
) -> Response:
    return await client.patch(
        f"/api/kp/bookings/{booking_id}/status",
        json={"status": "CANCELLED"},
        headers=headers,
    )


async def set_deadline(db_session: AsyncSession, booking_id: str, deadline: date):
    booking = (
        await db_session.execute(
            select(KpEventBooking).where(col(KpEventBooking.id) == UUID(booking_id))
        )
    ).scalar_one()
    booking.offer_cancel_until = deadline
    db_session.add(booking)
    await db_session.commit()


@pytest.fixture
async def offer_ready(
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> None:
    await complete_company_profile(company_headers)


@pytest.fixture
async def offered_booking(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offer_ready: None,
) -> dict[str, object]:
    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        local_today() + timedelta(days=3),
    )
    assert response.status_code == 200
    return response.json()


async def test_staff_offer_creates_a_booking_the_company_sees(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    offered_booking: dict[str, object],
):
    mine = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/my-booking", headers=company_headers
    )

    assert offered_booking["status"] == "REGISTERED"
    assert offered_booking["booth_zone_id"] == kp_setup.booth_zone_id
    assert (
        offered_booking["offer_cancel_until"]
        == (local_today() + timedelta(days=3)).isoformat()
    )
    assert mine.json()["id"] == offered_booking["id"]
    assert mine.json()["offer_cancel_until"] == offered_booking["offer_cancel_until"]


async def test_an_offer_ignores_a_full_zone_and_closed_registration(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offer_ready: None,
):
    full_zone_id = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        name="Gold",
        color="#AABBCC",
        capacity=0,
    )
    await client.patch(
        f"/api/kp/booth-zones/{full_zone_id}",
        json={"registration_open": False},
        headers=staff_headers,
    )
    event = (
        await db_session.execute(
            select(KpEvent).where(col(KpEvent.id) == UUID(kp_setup.event_id))
        )
    ).scalar_one()
    event.registration_open = local_today() - timedelta(days=10)
    event.registration_end = local_today() - timedelta(days=1)
    db_session.add(event)
    await db_session.commit()

    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        full_zone_id,
        local_today(),
    )

    assert response.status_code == 200
    assert response.json()["booth_zone_id"] == full_zone_id


async def test_an_offer_is_refused_when_the_company_already_booked(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offered_booking: dict[str, object],
):
    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        local_today() + timedelta(days=3),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booking_already_exists"


async def test_an_offer_needs_a_complete_company_profile(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
):
    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        local_today() + timedelta(days=3),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.company_profile_incomplete"


@pytest.mark.parametrize("days_from_today", [-1, 30])
async def test_an_offer_deadline_must_lie_between_today_and_the_event(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offer_ready: None,
    days_from_today: int,
):
    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        local_today() + timedelta(days=days_from_today),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "error.kp_offer_deadline_invalid"


async def test_the_company_can_cancel_an_offer_before_the_deadline(
    client: AsyncClient,
    company_headers: dict[str, str],
    offered_booking: dict[str, object],
):
    response = await cancel(client, company_headers, str(offered_booking["id"]))

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


async def test_the_company_can_cancel_an_offer_on_the_deadline_day(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    offered_booking: dict[str, object],
):
    await set_deadline(db_session, str(offered_booking["id"]), local_today())

    response = await cancel(client, company_headers, str(offered_booking["id"]))

    assert response.status_code == 200


async def test_the_company_can_cancel_a_confirmed_offer_before_the_deadline(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    offered_booking: dict[str, object],
):
    accepted = await client.post(
        f"/api/kp/bookings/{offered_booking['id']}/accept", headers=staff_headers
    )

    response = await cancel(client, company_headers, str(offered_booking["id"]))

    assert accepted.json()["status"] == "CONFIRMED"
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


async def test_the_company_cannot_cancel_an_offer_after_the_deadline(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    offered_booking: dict[str, object],
):
    await set_deadline(
        db_session, str(offered_booking["id"]), local_today() - timedelta(days=1)
    )

    response = await cancel(client, company_headers, str(offered_booking["id"]))

    assert response.status_code == 409
    assert response.json()["code"] == DEADLINE_PASSED_CODE


async def test_cancelling_an_offer_promotes_the_waitlist(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offer_ready: None,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    gold_id = await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        name="Gold",
        color="#AABBCC",
        capacity=1,
    )
    offered = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        gold_id,
        local_today() + timedelta(days=3),
    )
    other = await create_user(
        email="beta@example.com", password=None, company_name="Beta GmbH"
    )
    other_headers = {**await auth_headers(other), **csrf_headers}
    await complete_company_profile(other_headers)
    waiting = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={"booth_zone_id": kp_setup.booth_zone_id, "confirm_profile": True},
        headers=other_headers,
    )
    await client.put(
        f"/api/kp/bookings/{waiting.json()['id']}/upgrade-waitlist",
        json={"target_booth_zone_ids": [gold_id]},
        headers=other_headers,
    )

    await cancel(client, company_headers, offered.json()["id"])
    promoted = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{waiting.json()['id']}",
        headers=staff_headers,
    )

    assert promoted.json()["booth_zone_id"] == gold_id


async def test_staff_can_move_the_offer_deadline(
    client: AsyncClient,
    staff_headers: dict[str, str],
    offered_booking: dict[str, object],
):
    moved = local_today() + timedelta(days=5)

    response = await client.patch(
        f"/api/kp/bookings/{offered_booking['id']}/offer",
        json={"cancel_until": moved.isoformat()},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["offer_cancel_until"] == moved.isoformat()


async def test_a_moved_deadline_is_validated_too(
    client: AsyncClient,
    staff_headers: dict[str, str],
    offered_booking: dict[str, object],
):
    response = await client.patch(
        f"/api/kp/bookings/{offered_booking['id']}/offer",
        json={"cancel_until": (local_today() + timedelta(days=30)).isoformat()},
        headers=staff_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "error.kp_offer_deadline_invalid"


async def test_companies_cannot_offer_spots(
    client: AsyncClient,
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offer_ready: None,
):
    response = await offer(
        client,
        company_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        local_today() + timedelta(days=3),
    )

    assert response.status_code == 403


async def test_staff_without_president_role_cannot_offer_or_move_deadlines(
    client: AsyncClient,
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offered_booking: dict[str, object],
):
    headers = {**await auth_headers(staff_user), **csrf_headers}

    offered = await offer(
        client,
        headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        local_today() + timedelta(days=3),
    )
    moved = await client.patch(
        f"/api/kp/bookings/{offered_booking['id']}/offer",
        json={"cancel_until": local_today().isoformat()},
        headers=headers,
    )

    assert offered.status_code == 403
    assert moved.status_code == 403


async def test_offering_a_spot_mails_the_company(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offer_ready: None,
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.reset_mock()

    await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        local_today() + timedelta(days=3),
    )

    mail_stub.SendMail.assert_awaited_once()
    message = mail_stub.SendMail.await_args.args[0]
    assert decoded_subject(message) == (
        "VISIT: Platz für Kontaktparty angeboten"
        " / VISIT: A place at Kontaktparty offered to you"
    )
    assert (local_today() + timedelta(days=3)).isoformat() in message.plain_text
