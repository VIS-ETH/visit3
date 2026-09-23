import logging
from collections.abc import Callable, Coroutine, Sequence
from typing import Any, Protocol

from app.mail_templates.context import (
    BookingAcceptedContext,
    BookingContext,
    BookingFinalizedContext,
    BookingRejectedContext,
    BookingReminderContext,
    MailContext,
)
from app.mail_templates.keys import MailTemplateKey
from app.models.kp_event import KpEventBooking
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.booking_completeness import MissingItem
from app.services.mail_template_service import MailTemplateService

logger = logging.getLogger(__name__)

CURRENCY = "CHF"
NO_BOOTH_NUMBER = "-"
NO_REASON = "-"

ContextBuilder = Callable[[BookingContext], MailContext]


async def notify_best_effort(notification: Coroutine[Any, Any, None]) -> None:
    try:
        await notification
    except Exception:
        logger.exception("Booking notification failed")


class BookingNotifier(Protocol):
    async def booking_registered(self, booking: KpEventBooking) -> None:
        return None

    async def booking_finalized(self, booking: KpEventBooking) -> None: ...

    async def booking_accepted(self, booking: KpEventBooking) -> None: ...

    async def booking_rejected(self, booking: KpEventBooking, reason: str) -> None: ...

    async def booking_incomplete_at_deadline(
        self, booking: KpEventBooking, missing_items: Sequence[MissingItem]
    ) -> None: ...

    async def booking_incomplete_reminder(self, booking: KpEventBooking) -> None:
        return None

    async def waitlist_promoted(self, booking: KpEventBooking) -> None:
        return None


class SilentBookingNotifier(BookingNotifier):
    async def booking_finalized(self, booking: KpEventBooking) -> None:
        return None

    async def booking_accepted(self, booking: KpEventBooking) -> None:
        return None

    async def booking_rejected(self, booking: KpEventBooking, reason: str) -> None:
        return None

    async def booking_incomplete_at_deadline(
        self, booking: KpEventBooking, missing_items: Sequence[MissingItem]
    ) -> None:
        return None


def booking_path(booking: KpEventBooking) -> str:
    return f"/kp/{booking.event_id}/booking"


def money(cents: int) -> str:
    return f"{CURRENCY} {cents / 100:.2f}"


def same_context(context: BookingContext) -> MailContext:
    return context


class MailBookingNotifier:
    def __init__(
        self,
        mail_template_service: MailTemplateService,
        auth_service: AuthService,
    ) -> None:
        self.mail_template_service = mail_template_service
        self.auth_service = auth_service

    def _recipients(self, booking: KpEventBooking) -> Sequence[User]:
        return [user for user in booking.company.users if user.is_company]

    def _context(
        self, booking: KpEventBooking, user: User, login_url: str
    ) -> BookingContext:
        return BookingContext(
            name=user.display_name,
            company_name=booking.company.name,
            event_name=booking.event.name,
            booth_zone_name=booking.booth_zone.name,
            login_url=login_url,
        )

    async def _send_to_company(
        self,
        booking: KpEventBooking,
        key: MailTemplateKey,
        build: ContextBuilder = same_context,
    ) -> None:
        for user in self._recipients(booking):
            login_url = await self.auth_service.create_login_link(
                user, booking_path(booking)
            )
            context = self._context(booking, user, login_url)
            await self.mail_template_service.send(key, [user.email], build(context))

    async def booking_registered(self, booking: KpEventBooking) -> None:
        await self._send_to_company(booking, MailTemplateKey.BOOKING_REGISTERED)

    async def booking_finalized(self, booking: KpEventBooking) -> None:
        await self._send_to_company(
            booking,
            MailTemplateKey.BOOKING_FINALIZED,
            lambda context: BookingFinalizedContext(
                **context.variables(), total_price=money(booking.total_price)
            ),
        )

    async def booking_accepted(self, booking: KpEventBooking) -> None:
        await self._send_to_company(
            booking,
            MailTemplateKey.BOOKING_ACCEPTED,
            lambda context: BookingAcceptedContext(
                **context.variables(),
                booth_number=str(booking.booth_nr or NO_BOOTH_NUMBER),
            ),
        )

    async def booking_rejected(self, booking: KpEventBooking, reason: str) -> None:
        await self._send_to_company(
            booking,
            MailTemplateKey.BOOKING_REJECTED,
            lambda context: BookingRejectedContext(
                **context.variables(), reason=reason or NO_REASON
            ),
        )

    async def _send_incomplete_reminder(self, booking: KpEventBooking) -> None:
        deadline = booking.event.finalization_deadline.isoformat()
        await self._send_to_company(
            booking,
            MailTemplateKey.BOOKING_INCOMPLETE_REMINDER,
            lambda context: BookingReminderContext(
                **context.variables(), finalization_deadline=deadline
            ),
        )

    async def booking_incomplete_at_deadline(
        self, booking: KpEventBooking, missing_items: Sequence[MissingItem]
    ) -> None:
        await self._send_incomplete_reminder(booking)

    async def booking_incomplete_reminder(self, booking: KpEventBooking) -> None:
        await self._send_incomplete_reminder(booking)

    async def waitlist_promoted(self, booking: KpEventBooking) -> None:
        await self._send_to_company(booking, MailTemplateKey.WAITLIST_PROMOTED)
