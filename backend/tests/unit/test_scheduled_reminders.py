import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import scheduler as scheduler_module
from app.core.exceptions import MailUnavailable
from app.core.scheduler import Scheduler
from app.models.kp_event import KpEventBooking
from app.models.user import User
from app.services.booking_notifier import MailBookingNotifier
from app.services.booking_reminders import send_incomplete_booking_reminders
from tests.unit.test_booking_reminders import (
    FAKE_NOW,
    REMINDER_DAYS,
    make_booking,
    make_event,
    repository_with,
)


async def test_a_scheduled_job_runs_once_before_the_first_pause(
    monkeypatch: pytest.MonkeyPatch,
):
    events: list[str] = []

    async def job() -> None:
        events.append("run")

    async def stop_sleeping(seconds: float) -> None:
        events.append(f"sleep {seconds}")
        raise asyncio.CancelledError

    monkeypatch.setattr(scheduler_module.asyncio, "sleep", stop_sleeping)

    with pytest.raises(asyncio.CancelledError):
        await Scheduler()._loop(job, 86400)

    assert events == ["run", "sleep 86400"]


async def test_a_failed_reminder_is_not_marked_and_is_sent_again():
    booking = make_booking(make_event(deadline_in_days=REMINDER_DAYS), complete=False)
    kp_repository = repository_with([booking])
    notifier = AsyncMock()
    notifier.booking_incomplete_reminder.side_effect = [MailUnavailable("down"), None]

    await send_incomplete_booking_reminders(kp_repository, notifier, FAKE_NOW)

    kp_repository.update_booking.assert_not_awaited()

    await send_incomplete_booking_reminders(
        kp_repository, notifier, FAKE_NOW + timedelta(hours=1)
    )

    assert notifier.booking_incomplete_reminder.await_count == 2
    update = kp_repository.update_booking.await_args.args[1]
    assert update.reminder_sent_at == FAKE_NOW + timedelta(hours=1)


def booking_with_two_members() -> KpEventBooking:
    booking = make_booking(make_event(deadline_in_days=REMINDER_DAYS), complete=False)
    booking.company.users = [
        User(email="a@example.com", first_name="A", last_name="A", is_company=True),
        User(email="b@example.com", first_name="B", last_name="B", is_company=True),
    ]
    zone = MagicMock()
    zone.name = "Main hall"
    booking.booth_zone = zone
    return booking


def notifier_with(mail_template_service: AsyncMock) -> MailBookingNotifier:
    auth_service = AsyncMock()
    auth_service.create_login_link.return_value = "https://visit.test/link"
    return MailBookingNotifier(mail_template_service, auth_service)


async def test_one_failing_recipient_does_not_stop_the_mails_to_colleagues():
    mail_template_service = AsyncMock()
    mail_template_service.send.side_effect = [MailUnavailable("down"), None]

    await notifier_with(mail_template_service).booking_incomplete_reminder(
        booking_with_two_members()
    )

    recipients = [call.args[1] for call in mail_template_service.send.await_args_list]
    assert recipients == [["a@example.com"], ["b@example.com"]]


async def test_a_company_mail_fails_when_no_recipient_got_it():
    mail_template_service = AsyncMock()
    mail_template_service.send.side_effect = MailUnavailable("down")

    with pytest.raises(MailUnavailable):
        await notifier_with(mail_template_service).booking_incomplete_reminder(
            booking_with_two_members()
        )

    assert mail_template_service.send.await_count == 2
