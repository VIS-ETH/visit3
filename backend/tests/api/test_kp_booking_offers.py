import io
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import openpyxl
import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.dates import local_today
from app.models.kp_event import KpEventBooking
from app.models.user import User
from app.repositories.kp_repository import KpRepository
from app.services.booking_notifier import SilentBookingNotifier
from app.services.booking_offers import process_booking_offers
from tests.api.conftest import KpSetup, decoded_subject

OFFERED_SUBJECT = (
    "VISIT: Platz für Kontaktparty angeboten"
    " / VISIT: A place at Kontaktparty offered to you"
)
REGISTERED_SUBJECT = (
    "VISIT: Anmeldung für Kontaktparty erhalten"
    " / VISIT: Registration for Kontaktparty received"
)
TRANSITION_CODE = "error.kp_booking_status_transition_invalid"


def in_days(days: int) -> date:
    return local_today() + timedelta(days=days)


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
    deadline: date,
) -> Response:
    return await client.post(
        f"/api/kp/events/{event_id}/bookings/offer",
        json={
            "company_id": str(company_id),
            "booth_zone_id": zone_id,
            "deadline": deadline.isoformat(),
        },
        headers=headers,
    )


async def accept(
    client: AsyncClient,
    headers: dict[str, str],
    booking_id: str,
    *,
    confirm_profile: bool = True,
    accept_terms: bool = True,
) -> Response:
    return await client.post(
        f"/api/kp/bookings/{booking_id}/accept-offer",
        json={"confirm_profile": confirm_profile, "accept_terms": accept_terms},
        headers=headers,
    )


async def set_status(
    client: AsyncClient, headers: dict[str, str], booking_id: str, status: str
) -> Response:
    return await client.patch(
        f"/api/kp/bookings/{booking_id}/status",
        json={"status": status},
        headers=headers,
    )


async def stored_booking(db_session: AsyncSession, booking_id: str) -> KpEventBooking:
    db_session.expunge_all()
    return (
        await db_session.execute(
            select(KpEventBooking).where(col(KpEventBooking.id) == UUID(booking_id))
        )
    ).scalar_one()


async def set_deadline(db_session: AsyncSession, booking_id: str, deadline: date):
    booking = await stored_booking(db_session, booking_id)
    booking.offer_deadline = deadline
    db_session.add(booking)
    await db_session.commit()


async def other_company(
    name: str,
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> dict[str, str]:
    user = await create_user(
        email=f"{name}@example.com", password=None, company_name=f"{name} AG"
    )
    headers = {**await auth_headers(user), **csrf_headers}
    await complete_company_profile(headers)
    return headers


@pytest.fixture
async def profile_ready(
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> None:
    await complete_company_profile(company_headers)


@pytest.fixture
async def gold_id(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
) -> str:
    return await create_zone(
        client,
        staff_headers,
        kp_setup.event_id,
        name="Gold",
        color="#AABBCC",
        capacity=1,
    )


@pytest.fixture
async def offered(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    gold_id: str,
    profile_ready: None,
) -> dict[str, object]:
    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        gold_id,
        in_days(10),
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_an_offer_is_pending_and_holds_the_spot(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    gold_id: str,
    offered: dict[str, object],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    other_headers = await other_company(
        "beta", create_user, auth_headers, csrf_headers, complete_company_profile
    )

    mine = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/my-booking", headers=company_headers
    )
    blocked = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={"booth_zone_id": gold_id, "confirm_profile": True},
        headers=other_headers,
    )

    assert offered["status"] == "OFFERED"
    assert offered["offer_deadline"] == in_days(10).isoformat()
    assert mine.json()["status"] == "OFFERED"
    assert mine.json()["offer_deadline"] == in_days(10).isoformat()
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "error.kp_booth_zone_at_capacity"


async def test_an_offer_does_not_need_a_complete_profile(
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
        in_days(3),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "OFFERED"


async def test_accepting_with_terms_makes_a_registered_booking(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    offered: dict[str, object],
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.reset_mock()

    response = await accept(client, company_headers, str(offered["id"]))
    staff_view = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{offered['id']}",
        headers=staff_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REGISTERED"
    assert response.json()["status_changed_at"] is not None
    assert staff_view.json()["company_details_submitted"] is True
    mail_stub.SendMail.assert_awaited_once()
    assert decoded_subject(mail_stub.SendMail.await_args.args[0]) == REGISTERED_SUBJECT


async def test_accepting_without_the_terms_is_refused(
    client: AsyncClient,
    company_headers: dict[str, str],
    offered: dict[str, object],
):
    response = await accept(
        client, company_headers, str(offered["id"]), accept_terms=False
    )

    assert response.status_code == 422
    assert response.json()["code"] == "error.kp_terms_not_accepted"


async def test_accepting_needs_the_same_profile_confirmation_as_registering(
    client: AsyncClient,
    company_headers: dict[str, str],
    offered: dict[str, object],
):
    response = await accept(
        client, company_headers, str(offered["id"]), confirm_profile=False
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.company_profile_unconfirmed"


async def test_accepting_needs_the_same_profile_fields_as_registering(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
):
    pending = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(3),
    )

    response = await accept(client, company_headers, pending.json()["id"])

    assert response.status_code == 409
    assert response.json()["code"] == "error.company_profile_incomplete"


async def test_an_offer_can_be_accepted_on_its_deadline_day(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    offered: dict[str, object],
):
    await set_deadline(db_session, str(offered["id"]), local_today())

    response = await accept(client, company_headers, str(offered["id"]))

    assert response.status_code == 200
    assert response.json()["status"] == "REGISTERED"


async def test_an_offer_cannot_be_accepted_after_its_deadline(
    client: AsyncClient,
    db_session: AsyncSession,
    company_headers: dict[str, str],
    offered: dict[str, object],
):
    await set_deadline(db_session, str(offered["id"]), in_days(-1))

    response = await accept(client, company_headers, str(offered["id"]))

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_offer_expired"
    assert (await stored_booking(db_session, str(offered["id"]))).status == "OFFERED"


async def test_only_a_pending_offer_can_be_accepted(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    registered = await register_booking(company_headers, kp_setup)

    response = await accept(client, company_headers, registered.json()["id"])

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booking_not_offered"


async def test_another_company_cannot_accept_the_offer(
    client: AsyncClient,
    offered: dict[str, object],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    other_headers = await other_company(
        "intruder", create_user, auth_headers, csrf_headers, complete_company_profile
    )

    response = await accept(client, other_headers, str(offered["id"]))

    assert response.status_code in (403, 404)


async def test_staff_cannot_accept_on_behalf_of_the_company(
    client: AsyncClient,
    staff_headers: dict[str, str],
    offered: dict[str, object],
):
    offer_response = await accept(client, staff_headers, str(offered["id"]))
    confirm_response = await client.post(
        f"/api/kp/bookings/{offered['id']}/accept", headers=staff_headers
    )

    assert offer_response.status_code == 403
    assert confirm_response.status_code == 400
    assert confirm_response.json()["code"] == TRANSITION_CODE


async def test_an_accepted_offer_follows_the_normal_cancel_rules(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    offered: dict[str, object],
):
    await accept(client, company_headers, str(offered["id"]))
    await client.post(f"/api/kp/bookings/{offered['id']}/accept", headers=staff_headers)

    response = await set_status(
        client, company_headers, str(offered["id"]), "CANCELLED"
    )

    assert response.status_code == 400
    assert response.json()["code"] == TRANSITION_CODE


async def test_declining_frees_the_spot_for_the_waitlist(
    client: AsyncClient,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    gold_id: str,
    offered: dict[str, object],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    waiting_headers = await other_company(
        "waiting", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    waiting = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={"booth_zone_id": kp_setup.booth_zone_id, "confirm_profile": True},
        headers=waiting_headers,
    )
    await client.put(
        f"/api/kp/bookings/{waiting.json()['id']}/upgrade-waitlist",
        json={"target_booth_zone_ids": [gold_id]},
        headers=waiting_headers,
    )

    declined = await set_status(
        client, company_headers, str(offered["id"]), "CANCELLED"
    )
    promoted = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{waiting.json()['id']}",
        headers=staff_headers,
    )

    assert declined.status_code == 200
    assert declined.json()["status"] == "CANCELLED"
    assert promoted.json()["booth_zone_id"] == gold_id


async def test_the_expiry_job_frees_an_overdue_offer_for_the_waitlist(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    gold_id: str,
    offered: dict[str, object],
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    waiting_headers = await other_company(
        "waiting", create_user, auth_headers, csrf_headers, complete_company_profile
    )
    waiting = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={"booth_zone_id": kp_setup.booth_zone_id, "confirm_profile": True},
        headers=waiting_headers,
    )
    await client.put(
        f"/api/kp/bookings/{waiting.json()['id']}/upgrade-waitlist",
        json={"target_booth_zone_ids": [gold_id]},
        headers=waiting_headers,
    )
    await set_deadline(db_session, str(offered["id"]), in_days(-1))

    await process_booking_offers(
        KpRepository(db_session), SilentBookingNotifier(), datetime.now(timezone.utc)
    )
    promoted = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/bookings/{waiting.json()['id']}",
        headers=staff_headers,
    )

    assert (await stored_booking(db_session, str(offered["id"]))).status == "EXPIRED"
    assert promoted.json()["booth_zone_id"] == gold_id


async def test_the_expiry_job_keeps_an_offer_on_its_deadline_day(
    db_session: AsyncSession, offered: dict[str, object]
):
    await set_deadline(db_session, str(offered["id"]), local_today())

    await process_booking_offers(
        KpRepository(db_session), SilentBookingNotifier(), datetime.now(timezone.utc)
    )

    assert (await stored_booking(db_session, str(offered["id"]))).status == "OFFERED"


async def test_moving_the_deadline_restarts_the_reminders(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    offered: dict[str, object],
):
    booking = await stored_booking(db_session, str(offered["id"]))
    booking.offer_week_reminder_sent_at = datetime.now(timezone.utc)
    booking.offer_day_reminder_sent_at = datetime.now(timezone.utc)
    db_session.add(booking)
    await db_session.commit()

    response = await client.patch(
        f"/api/kp/bookings/{offered['id']}/offer",
        json={"deadline": in_days(20).isoformat()},
        headers=staff_headers,
    )
    moved = await stored_booking(db_session, str(offered["id"]))

    assert response.status_code == 200
    assert response.json()["offer_deadline"] == in_days(20).isoformat()
    assert moved.offer_week_reminder_sent_at is None
    assert moved.offer_day_reminder_sent_at is None
    assert moved.offer_made_on == local_today()


async def test_an_accepted_offer_keeps_no_editable_deadline(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    offered: dict[str, object],
):
    await accept(client, company_headers, str(offered["id"]))

    response = await client.patch(
        f"/api/kp/bookings/{offered['id']}/offer",
        json={"deadline": in_days(20).isoformat()},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booking_not_offered"


@pytest.mark.parametrize("days_from_today", [-1, 30])
async def test_an_offer_deadline_must_lie_between_today_and_the_event(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    days_from_today: int,
):
    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(days_from_today),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "error.kp_offer_deadline_invalid"


async def test_an_offer_is_refused_when_the_company_already_booked(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offered: dict[str, object],
):
    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(3),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.kp_booking_already_exists"


async def test_a_pending_offer_cannot_be_edited_like_a_booking(
    client: AsyncClient,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    offered: dict[str, object],
):
    services = await client.post(
        f"/api/kp/bookings/{offered['id']}/services",
        json={"services": [{"service_id": kp_setup.service_id, "quantity": 1}]},
        headers=company_headers,
    )
    nametags = await client.put(
        f"/api/kp/bookings/{offered['id']}/nametags",
        json={
            "name_tags": [
                {"first_name": "Ada", "last_name": "Lovelace", "position": "CTO"}
            ]
        },
        headers=company_headers,
    )

    assert services.status_code == 409
    assert services.json()["code"] == "error.kp_offer_pending"
    assert nametags.status_code == 409
    assert nametags.json()["code"] == "error.kp_offer_pending"


async def test_offering_a_place_asks_the_company_to_confirm_by_the_deadline(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.reset_mock()

    await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(3),
    )

    mail_stub.SendMail.assert_awaited_once()
    message = mail_stub.SendMail.await_args.args[0]
    assert decoded_subject(message) == OFFERED_SUBJECT
    assert in_days(3).isoformat() in message.plain_text
    assert "bestätigen" in message.plain_text
    assert "confirm" in message.plain_text


async def test_companies_cannot_offer_places(
    client: AsyncClient,
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
):
    response = await offer(
        client,
        company_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(3),
    )

    assert response.status_code == 403


async def test_staff_without_president_role_cannot_offer_or_move_deadlines(
    client: AsyncClient,
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    offered: dict[str, object],
):
    headers = {**await auth_headers(staff_user), **csrf_headers}

    offered_again = await offer(
        client,
        headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(3),
    )
    moved = await client.patch(
        f"/api/kp/bookings/{offered['id']}/offer",
        json={"deadline": in_days(4).isoformat()},
        headers=headers,
    )

    assert offered_again.status_code == 403
    assert moved.status_code == 403


async def test_a_pending_offer_is_left_out_of_participant_exports(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    company_user: User,
):
    included_zone = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={
            "name": "Included",
            "color": "#123456",
            "capacity": 2,
            "included_services": [
                {"service_id": kp_setup.service_id, "included_quantity": 1}
            ],
        },
        headers=staff_headers,
    )
    await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        included_zone.json()["id"],
        in_days(3),
    )
    exports = f"/api/kp/events/{kp_setup.event_id}/exports"

    workbook = openpyxl.load_workbook(
        io.BytesIO(
            (
                await client.get(f"{exports}/companies/download", headers=staff_headers)
            ).content
        )
    )
    booked_services = (
        await client.get(f"{exports}/booked-services/download", headers=staff_headers)
    ).content.decode("utf-8-sig")
    bookings_list = (
        await client.get(f"{exports}/bookings/download", headers=staff_headers)
    ).content.decode("utf-8-sig")

    company_names = [
        row[0].value
        for sheet in workbook.worksheets
        for row in sheet.iter_rows(min_row=2)
    ]
    assert "Acme AG" not in company_names
    assert "Acme AG" not in booked_services
    assert "Acme AG" in bookings_list
    assert "OFFERED" in bookings_list
