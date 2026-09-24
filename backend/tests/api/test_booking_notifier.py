from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock
from uuid import UUID

import grpc
import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kp_event import KpEventBooking
from app.repositories.kp_repository import KpRepository
from app.services.auth_service import AuthService
from app.services.booking_notifier import MailBookingNotifier
from app.services.mail_template_service import MailTemplateService
from tests.api.conftest import KpSetup

REJECTION_REASON = "Die Standzone ist ausgebucht."

EXPECTED_SUBJECTS = {
    "booking_registered": "VISIT: Anmeldung für Kontaktparty erhalten"
    " / VISIT: Registration for Kontaktparty received",
    "booking_finalized": "VISIT: Buchung für Kontaktparty abgeschlossen"
    " / VISIT: Booking for Kontaktparty completed",
    "booking_accepted": "VISIT: Buchung für Kontaktparty bestätigt"
    " / VISIT: Booking for Kontaktparty confirmed",
    "booking_rejected": "VISIT: Buchung für Kontaktparty abgelehnt"
    " / VISIT: Booking for Kontaktparty rejected",
    "booking_incomplete_reminder": "VISIT: Buchung für Kontaktparty ist unvollständig"
    " / VISIT: Your booking for Kontaktparty is incomplete",
    "waitlist_promoted": "VISIT: Platz in Main hall frei geworden"
    " / VISIT: A spot in Main hall became available",
}

NOTIFICATIONS: dict[
    str, Callable[[MailBookingNotifier, KpEventBooking], Awaitable[None]]
] = {
    "booking_registered": lambda notifier, booking: notifier.booking_registered(
        booking
    ),
    "booking_finalized": lambda notifier, booking: notifier.booking_finalized(booking),
    "booking_accepted": lambda notifier, booking: notifier.booking_accepted(booking),
    "booking_rejected": lambda notifier, booking: notifier.booking_rejected(
        booking, REJECTION_REASON
    ),
    "booking_incomplete_reminder": (
        lambda notifier, booking: notifier.booking_incomplete_reminder(booking)
    ),
    "waitlist_promoted": lambda notifier, booking: notifier.waitlist_promoted(booking),
}


@pytest.fixture
def notifier(
    mail_template_service: MailTemplateService, auth_service: AuthService
) -> MailBookingNotifier:
    return MailBookingNotifier(mail_template_service, auth_service)


@pytest.fixture
async def booking(
    db_session: AsyncSession,
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
) -> KpEventBooking:
    registered = await register_booking(company_headers, kp_setup)
    loaded = await KpRepository(db_session).get_booking_by_id(
        UUID(registered.json()["id"])
    )
    assert loaded is not None
    return loaded


@pytest.mark.parametrize("method_name", sorted(EXPECTED_SUBJECTS))
async def test_every_notification_reaches_the_company_user_once(
    client: AsyncClient,
    notifier: MailBookingNotifier,
    booking: KpEventBooking,
    mail_stub: AsyncMock,
    method_name: str,
):
    mail_stub.SendMail.reset_mock()

    await NOTIFICATIONS[method_name](notifier, booking)

    mail_stub.SendMail.assert_awaited_once()
    message = mail_stub.SendMail.await_args.args[0]
    assert [address.mail_address.address for address in message.to] == [
        "company@example.com"
    ]
    assert message.subject == EXPECTED_SUBJECTS[method_name]
    assert "/auth/link/" in message.plain_text


async def test_rejection_reason_is_rendered(
    client: AsyncClient,
    notifier: MailBookingNotifier,
    booking: KpEventBooking,
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.reset_mock()

    await notifier.booking_rejected(booking, REJECTION_REASON)

    message = mail_stub.SendMail.await_args.args[0]
    assert REJECTION_REASON in message.plain_text


async def test_rejection_without_a_reason_still_renders(
    client: AsyncClient,
    notifier: MailBookingNotifier,
    booking: KpEventBooking,
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.reset_mock()

    await notifier.booking_rejected(booking, "")

    mail_stub.SendMail.assert_awaited_once()


async def test_registering_a_booking_sends_the_registration_mail(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.reset_mock()

    registered = await register_booking(company_headers, kp_setup)

    assert registered.status_code == 200
    mail_stub.SendMail.assert_awaited_once()
    message = mail_stub.SendMail.await_args.args[0]
    assert message.subject == EXPECTED_SUBJECTS["booking_registered"]


async def test_rejecting_a_booking_sends_the_rejection_mail(
    client: AsyncClient,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
    mail_stub: AsyncMock,
):
    registered = await register_booking(company_headers, kp_setup)
    mail_stub.SendMail.reset_mock()

    rejected = await client.post(
        f"/api/kp/bookings/{registered.json()['id']}/reject",
        json={"reason": REJECTION_REASON},
        headers=staff_headers,
    )

    assert rejected.status_code == 200
    mail_stub.SendMail.assert_awaited_once()
    message = mail_stub.SendMail.await_args.args[0]
    assert message.subject == EXPECTED_SUBJECTS["booking_rejected"]
    assert REJECTION_REASON in message.plain_text


async def test_finalized_mail_contains_the_total_price(
    client: AsyncClient,
    notifier: MailBookingNotifier,
    booking: KpEventBooking,
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.reset_mock()

    await notifier.booking_finalized(booking)

    message = mail_stub.SendMail.await_args.args[0]
    assert "CHF 150.00" in message.plain_text


async def test_registration_succeeds_when_the_mail_service_fails(
    company_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.side_effect = grpc.RpcError()

    registered = await register_booking(company_headers, kp_setup)

    assert registered.status_code == 200
