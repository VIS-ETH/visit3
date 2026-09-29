from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import grpc
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core import dates, deps
from app.core.dates import local_today
from app.models.company import KpCompanyProfile
from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpEventBooking,
    KpEventRegistrationException,
)
from app.models.user import User
from app.services.pdf_service import PdfService, RenderedImage
from tests.api.conftest import (
    KpSetup,
    company_profile_payload,
    first_member_id,
    kp_payload,
)

GOLD_COLOR = "#AABBCC"
LOGIN_EMAIL = "company@example.com"
STUDENT_EMAIL = "jobs@acme.example"
OFFER_EXPIRED_CODE = "error.kp_offer_expired"
DEADLINE_INVALID_CODE = "error.kp_offer_deadline_invalid"


@dataclass(frozen=True)
class Rival:
    user: User
    headers: dict[str, str]


async def create_zone(
    client: AsyncClient,
    headers: dict[str, str],
    event_id: str,
    name: str = "Gold",
    color: str = GOLD_COLOR,
    capacity: int = 1,
) -> str:
    response = await client.post(
        f"/api/kp/events/{event_id}/booth-zones",
        json={"name": name, "color": color, "capacity": capacity},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["id"]


async def offer(
    client: AsyncClient,
    headers: dict[str, str],
    event_id: str,
    company_id: object,
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


async def accept_offer(
    client: AsyncClient, headers: dict[str, str], booking_id: str
) -> Response:
    return await client.post(
        f"/api/kp/bookings/{booking_id}/accept-offer",
        json={"confirm_profile": True, "accept_terms": True},
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


async def close_zone(client: AsyncClient, headers: dict[str, str], zone_id: str):
    response = await client.patch(
        f"/api/kp/booth-zones/{zone_id}",
        json={"registration_open": False},
        headers=headers,
    )
    assert response.status_code == 200


async def register(
    client: AsyncClient, headers: dict[str, str], event_id: str, zone_id: str
) -> Response:
    return await client.post(
        f"/api/kp/events/{event_id}/bookings/register",
        json={"booth_zone_id": zone_id, "confirm_profile": True},
        headers=headers,
    )


async def staff_booking(
    client: AsyncClient, headers: dict[str, str], event_id: str, booking_id: str
) -> dict[str, object]:
    response = await client.get(
        f"/api/kp/events/{event_id}/bookings/{booking_id}", headers=headers
    )
    return response.json()


async def snapshot(
    db_session: AsyncSession, booking_id: str
) -> KpBookingCompanyDetails:
    statement = (
        select(KpBookingCompanyDetails)
        .where(col(KpBookingCompanyDetails.booking_id) == UUID(booking_id))
        .execution_options(populate_existing=True)
    )
    return (await db_session.execute(statement)).scalar_one()


def in_days(days: int) -> date:
    return local_today() + timedelta(days=days)


@pytest.fixture
async def ready_company(
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> None:
    await complete_company_profile(company_headers)


@pytest.fixture
async def rival(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
) -> Rival:
    user = await create_user(
        email="beta@example.com", password=None, company_name="Beta GmbH"
    )
    headers = {**await auth_headers(user), **csrf_headers}
    await complete_company_profile(headers)
    return Rival(user=user, headers=headers)


@pytest.fixture
async def gold_offer(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    ready_company: None,
) -> tuple[str, str]:
    gold_id = await create_zone(client, staff_headers, kp_setup.event_id)
    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        gold_id,
        in_days(3),
    )
    assert response.status_code == 200
    return gold_id, response.json()["id"]


async def waitlist_for(
    client: AsyncClient, rival: Rival, kp_setup: KpSetup, zone_id: str
) -> str:
    booking = await register(
        client, rival.headers, kp_setup.event_id, kp_setup.booth_zone_id
    )
    joined = await client.put(
        f"/api/kp/bookings/{booking.json()['id']}/upgrade-waitlist",
        json={"target_booth_zone_ids": [zone_id]},
        headers=rival.headers,
    )
    assert joined.status_code == 200
    return booking.json()["id"]


async def test_a_cancelled_offer_in_a_closed_zone_is_not_given_to_the_waitlist(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    gold_offer: tuple[str, str],
    rival: Rival,
):
    gold_id, offered_id = gold_offer
    waiting_id = await waitlist_for(client, rival, kp_setup, gold_id)
    await close_zone(client, staff_headers, gold_id)

    cancelled = await set_status(client, company_headers, offered_id, "CANCELLED")
    waiting = await staff_booking(client, staff_headers, kp_setup.event_id, waiting_id)

    assert cancelled.status_code == 200
    assert waiting["booth_zone_id"] == kp_setup.booth_zone_id


async def test_an_exception_lets_the_waitlist_take_a_cancelled_offer_in_a_closed_zone(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    gold_offer: tuple[str, str],
    rival: Rival,
):
    gold_id, offered_id = gold_offer
    waiting_id = await waitlist_for(client, rival, kp_setup, gold_id)
    await close_zone(client, staff_headers, gold_id)
    db_session.add(
        KpEventRegistrationException(
            event_id=UUID(kp_setup.event_id),
            company_id=UUID(str(rival.user.company_id)),
            allowed_until=in_days(1),
        )
    )
    await db_session.commit()

    await set_status(client, company_headers, offered_id, "CANCELLED")
    waiting = await staff_booking(client, staff_headers, kp_setup.event_id, waiting_id)

    assert waiting["booth_zone_id"] == gold_id


async def test_a_clone_copies_zones_but_no_bookings_or_offers(
    client: AsyncClient,
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    gold_offer: tuple[str, str],
):
    gold_id, offered_id = gold_offer
    await close_zone(client, staff_headers, gold_id)

    clone = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/clone",
        json=kp_payload("Kontaktparty clone"),
        headers=staff_headers,
    )
    clone_id = clone.json()["id"]
    bookings = await client.get(
        f"/api/kp/events/{clone_id}/bookings", headers=staff_headers
    )
    zones = await client.get(
        f"/api/kp/events/{clone_id}/booth-zones", headers=staff_headers
    )
    source = await staff_booking(client, staff_headers, kp_setup.event_id, offered_id)

    assert clone.status_code == 200
    assert bookings.json() == []
    assert [zone["name"] for zone in zones.json()] == ["Gold", "Main hall"]
    assert all(zone["registration_open"] for zone in zones.json())
    assert gold_id not in {zone["id"] for zone in zones.json()}
    assert source["offer_deadline"] == in_days(3).isoformat()


async def test_reordering_zones_keeps_an_offered_booking(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    gold_offer: tuple[str, str],
):
    gold_id, offered_id = gold_offer

    reordered = await client.put(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones/order",
        json={"booth_zone_ids": [gold_id, kp_setup.booth_zone_id]},
        headers=staff_headers,
    )
    mine = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/my-booking", headers=company_headers
    )
    available = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones/available",
        headers=company_headers,
    )

    assert reordered.status_code == 200
    assert mine.json()["id"] == offered_id
    assert mine.json()["booth_zone_id"] == gold_id
    assert mine.json()["offer_deadline"] == in_days(3).isoformat()
    assert [zone["id"] for zone in available.json()] == [
        gold_id,
        kp_setup.booth_zone_id,
    ]


async def test_an_offer_reaches_a_company_whose_general_email_is_its_login(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    ready_company: None,
):
    statement = select(KpCompanyProfile).where(
        col(KpCompanyProfile.company_id) == company_user.company_id
    )
    profile = (await db_session.execute(statement)).scalar_one()
    profile.general_email = LOGIN_EMAIL
    db_session.add(profile)
    await db_session.commit()

    offered = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(3),
    )
    accepted = await accept_offer(client, company_headers, offered.json()["id"])
    saved = await client.put(
        "/api/company/me/profile",
        json=company_profile_payload(
            kp_contact_user_id=await first_member_id(client, company_headers),
            general_email=LOGIN_EMAIL,
            billing_city="Bern",
        ),
        headers=company_headers,
    )

    assert offered.status_code == 200
    assert accepted.json()["missing_items"] == []
    assert (await snapshot(db_session, offered.json()["id"])).general_email == (
        LOGIN_EMAIL
    )
    assert saved.status_code == 200


@pytest.fixture
def recording_pdf_service(api_app: FastAPI):
    service = AsyncMock(spec=PdfService)
    service.render_png.return_value = RenderedImage(png=b"\x89PNG", metadata=False)
    api_app.dependency_overrides[deps.get_pdf_service] = lambda: service
    yield service
    api_app.dependency_overrides.pop(deps.get_pdf_service, None)


async def test_the_student_email_reaches_an_offered_booking_and_the_booklet(
    client: AsyncClient,
    db_session: AsyncSession,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    recording_pdf_service: AsyncMock,
):
    payload = company_profile_payload(
        kp_contact_user_id=await first_member_id(client, company_headers),
        student_contact_email=STUDENT_EMAIL,
    )
    await client.put("/api/company/me/profile", json=payload, headers=company_headers)
    gold_id = await create_zone(client, staff_headers, kp_setup.event_id)

    offered = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        gold_id,
        in_days(3),
    )
    await accept_offer(client, company_headers, offered.json()["id"])
    preview = await client.post(
        f"/api/company/{company_user.company_id}/profile/booklet-page",
        json=payload,
        headers=staff_headers,
    )
    entry = recording_pdf_service.render_png.await_args.kwargs["data"]

    assert (await snapshot(db_session, offered.json()["id"])).student_contact_email == (
        STUDENT_EMAIL
    )
    assert preview.status_code == 200
    assert entry["student_contact_email"] == STUDENT_EMAIL
    assert entry["zone_color"] == GOLD_COLOR


async def test_a_pending_offer_cannot_switch_zones_but_can_be_declined(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    gold_offer: tuple[str, str],
):
    _, offered_id = gold_offer

    switched = await client.post(
        f"/api/kp/bookings/{offered_id}/switch-zone",
        json={"booth_zone_id": kp_setup.booth_zone_id},
        headers=company_headers,
    )
    cancelled = await set_status(client, company_headers, offered_id, "CANCELLED")

    assert switched.status_code == 409
    assert cancelled.status_code == 200


async def test_an_accepted_offer_cannot_switch_into_a_closed_zone(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    gold_offer: tuple[str, str],
):
    _, offered_id = gold_offer
    await accept_offer(client, company_headers, offered_id)
    await close_zone(client, staff_headers, kp_setup.booth_zone_id)

    switched = await client.post(
        f"/api/kp/bookings/{offered_id}/switch-zone",
        json={"booth_zone_id": kp_setup.booth_zone_id},
        headers=company_headers,
    )

    assert switched.status_code == 403
    assert switched.json()["code"] == "error.kp_zone_registration_closed"


async def test_an_offer_into_a_zone_of_another_event_is_refused(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    ready_company: None,
):
    other = await client.post(
        "/api/kp/create", json=kp_payload("Other party"), headers=staff_headers
    )
    foreign_zone = await create_zone(client, staff_headers, other.json()["id"])

    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        foreign_zone,
        in_days(3),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_booth_zone_event_mismatch"


async def test_an_offer_into_an_unknown_zone_or_event_is_not_found(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    ready_company: None,
):
    unknown_zone = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        str(uuid4()),
        in_days(3),
    )
    unknown_event = await offer(
        client,
        staff_headers,
        str(uuid4()),
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(3),
    )

    assert unknown_zone.status_code == 404
    assert unknown_event.status_code == 404


async def test_a_company_that_cancelled_before_can_receive_an_offer(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)
    await set_status(client, company_headers, booking.json()["id"], "CANCELLED")

    response = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(3),
    )

    assert response.status_code == 200
    assert response.json()["id"] != booking.json()["id"]


FROZEN_DAY = date(2026, 11, 2)


def utc_instant(day: date, hour: int, minute: int) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc)


@pytest.fixture
def freeze_now(monkeypatch: pytest.MonkeyPatch) -> Callable[[datetime], None]:
    def freeze(instant: datetime) -> None:
        monkeypatch.setattr(
            dates, "datetime", MagicMock(now=lambda tz=None: instant.astimezone(tz))
        )

    return freeze


@pytest.fixture
async def closed_event(
    client: AsyncClient,
    staff_headers: dict[str, str],
    freeze_now: Callable[[datetime], None],
    ready_company: None,
) -> KpSetup:
    freeze_now(utc_instant(FROZEN_DAY - timedelta(days=1), 23, 30))
    event = await client.post(
        "/api/kp/create",
        json={
            "name": "Zurich party",
            "registration_open": "2026-10-20",
            "registration_end": "2026-11-01",
            "finalization_deadline": "2026-11-05",
            "nametags_deadline": "2026-11-06",
            "event_date": "2026-11-20",
        },
        headers=staff_headers,
    )
    event_id = event.json()["id"]
    zone_id = await create_zone(client, staff_headers, event_id, capacity=3)
    return KpSetup(event_id=event_id, booth_zone_id=zone_id, service_id="")


async def test_offers_use_the_zurich_day_after_registration_closed(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    closed_event: KpSetup,
):
    registered = await register(
        client, company_headers, closed_event.event_id, closed_event.booth_zone_id
    )
    yesterday = await offer(
        client,
        staff_headers,
        closed_event.event_id,
        company_user.company_id,
        closed_event.booth_zone_id,
        FROZEN_DAY - timedelta(days=1),
    )
    today = await offer(
        client,
        staff_headers,
        closed_event.event_id,
        company_user.company_id,
        closed_event.booth_zone_id,
        FROZEN_DAY,
    )

    assert registered.status_code == 403
    assert registered.json()["code"] == "error.kp_registration_closed"
    assert yesterday.status_code == 422
    assert yesterday.json()["code"] == DEADLINE_INVALID_CODE
    assert today.status_code == 200


@pytest.mark.parametrize(
    ("hour", "minute", "expected_status"),
    [(22, 59, 200), (23, 0, 409)],
)
async def test_an_offer_can_be_accepted_until_the_end_of_its_zurich_day(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    closed_event: KpSetup,
    freeze_now: Callable[[datetime], None],
    hour: int,
    minute: int,
    expected_status: int,
):
    deadline = FROZEN_DAY + timedelta(days=1)
    offered = await offer(
        client,
        staff_headers,
        closed_event.event_id,
        company_user.company_id,
        closed_event.booth_zone_id,
        deadline,
    )
    freeze_now(utc_instant(deadline, hour, minute))

    response = await accept_offer(client, company_headers, offered.json()["id"])

    assert response.status_code == expected_status
    if expected_status == 409:
        assert response.json()["code"] == OFFER_EXPIRED_CODE


async def test_a_cancelled_offer_cannot_be_rebooked_after_registration_closed(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    closed_event: KpSetup,
):
    offered = await offer(
        client,
        staff_headers,
        closed_event.event_id,
        company_user.company_id,
        closed_event.booth_zone_id,
        FROZEN_DAY + timedelta(days=1),
    )
    await set_status(client, company_headers, offered.json()["id"], "CANCELLED")

    rebooked = await register(
        client, company_headers, closed_event.event_id, closed_event.booth_zone_id
    )
    stored = await client.get(
        f"/api/kp/events/{closed_event.event_id}/my-booking",
        headers=company_headers,
    )

    assert rebooked.status_code == 403
    assert stored.json()["status"] == "CANCELLED"


async def test_an_offered_place_counts_against_the_zone_capacity(
    client: AsyncClient,
    db_session: AsyncSession,
    kp_setup: KpSetup,
    gold_offer: tuple[str, str],
    rival: Rival,
):
    gold_id, offered_id = gold_offer

    refused = await register(client, rival.headers, kp_setup.event_id, gold_id)
    booking = (
        await db_session.execute(
            select(KpEventBooking).where(col(KpEventBooking.id) == UUID(offered_id))
        )
    ).scalar_one()

    assert refused.status_code == 409
    assert booking.offer_deadline == in_days(3)


async def test_moving_the_deadline_of_a_regular_booking_is_refused(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
):
    booking = await register_booking(company_headers, kp_setup)
    booking_id = booking.json()["id"]
    await client.post(f"/api/kp/bookings/{booking_id}/accept", headers=staff_headers)

    moved = await client.patch(
        f"/api/kp/bookings/{booking_id}/offer",
        json={"deadline": in_days(3).isoformat()},
        headers=staff_headers,
    )
    cancelled = await set_status(client, company_headers, booking_id, "CANCELLED")

    assert moved.status_code == 409
    assert moved.json()["code"] == "error.kp_booking_not_offered"
    assert cancelled.json()["code"] == "error.kp_booking_status_transition_invalid"


async def test_an_offer_is_stored_when_the_mail_service_fails(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    company_user: User,
    kp_setup: KpSetup,
    ready_company: None,
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.side_effect = grpc.RpcError()

    offered = await offer(
        client,
        staff_headers,
        kp_setup.event_id,
        company_user.company_id,
        kp_setup.booth_zone_id,
        in_days(3),
    )
    mine = await client.get(
        f"/api/kp/events/{kp_setup.event_id}/my-booking", headers=company_headers
    )

    assert offered.status_code == 200
    assert mine.json()["id"] == offered.json()["id"]
