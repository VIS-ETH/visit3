from datetime import date
from uuid import UUID

from app.core.auth_context import (
    require_assigned_company_user,
    require_kp_president_user,
)
from app.core.dates import local_today, utc_now
from app.core.exceptions import (
    CompanyNotFound,
    KpBookingAlreadyExists,
    KpBookingNotOffered,
    KpOfferDeadlineInvalid,
    KpOfferExpired,
    KpTermsNotAccepted,
)
from app.models.company import Company
from app.models.kp_event import KpBookingStatus, KpEvent
from app.schemas.kp import (
    AcceptOfferRequest,
    BookingResponse,
    BookingWithCompanyAndBoothZoneResponse,
    CreateBookingInput,
    OfferBookingRequest,
    UpdateBookingInput,
    UpdateBookingOfferRequest,
)
from app.services.booking_notifier import notify_best_effort
from app.services.kp_service.quantities import zone_included_quantities
from app.services.kp_service.responses import ResponsesMixin


class OffersMixin(ResponsesMixin):
    def _ensure_offer_deadline(
        self, event: KpEvent, deadline: date, context: str
    ) -> None:
        if not local_today() <= deadline < event.event_date:
            raise KpOfferDeadlineInvalid(f"{context}:{event.id}:{deadline}")

    async def offer_booking(
        self, event_id: UUID, request: OfferBookingRequest
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_kp_president_user(self.current_user)
        event = await self._get_event(event_id)
        self._ensure_offer_deadline(event, request.deadline, "offer_booking")
        zone = await self._get_event_booth_zone(
            request.booth_zone_id, event_id, "offer_booking"
        )
        company = await self.kp_repository.lock_model_by_id(Company, request.company_id)
        if company is None:
            raise CompanyNotFound(f"offer_booking:company:{request.company_id}")
        await self.kp_repository.lock_model_by_id(KpEvent, event_id)
        existing = await self.kp_repository.get_company_active_booking_for_event(
            event_id, request.company_id
        )
        if existing is not None:
            raise KpBookingAlreadyExists(
                f"offer_booking:already_exists:{event_id}:{request.company_id}"
            )
        locked_zone = await self._lock_zone_until_booking_is_inserted(
            zone.id, "offer_booking"
        )
        await self._ensure_zone_not_full(event_id, locked_zone, "offer_booking")
        booking = await self.kp_repository.create_booking(
            event_id=event_id,
            company_id=request.company_id,
            booth_zone_id=zone.id,
            create_booking_input=CreateBookingInput(
                status=KpBookingStatus.OFFERED,
                offer_deadline=request.deadline,
                offer_made_on=local_today(),
            ),
            included_quantities=zone_included_quantities(locked_zone),
        )
        await notify_best_effort(
            self.notifier.booking_offered(booking, request.deadline)
        )
        return await self._build_staff_booking_response(booking)

    async def update_booking_offer(
        self, booking_id: UUID, request: UpdateBookingOfferRequest
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_kp_president_user(self.current_user)
        booking = await self._get_booking(booking_id, lock=True)
        if booking.status != KpBookingStatus.OFFERED:
            raise KpBookingNotOffered(f"update_booking_offer:not_offered:{booking_id}")
        self._ensure_offer_deadline(
            booking.event, request.deadline, "update_booking_offer"
        )
        updated = await self.kp_repository.update_booking(
            booking,
            UpdateBookingInput(
                offer_deadline=request.deadline,
                offer_made_on=local_today(),
                offer_week_reminder_sent_at=None,
                offer_day_reminder_sent_at=None,
            ),
        )
        return await self._build_staff_booking_response(updated)

    async def accept_offer(
        self, booking_id: UUID, request: AcceptOfferRequest
    ) -> BookingResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "accept_offer", lock=True
        )
        if booking.status != KpBookingStatus.OFFERED:
            raise KpBookingNotOffered(f"accept_offer:not_offered:{booking_id}")
        if not booking.is_offer_open():
            raise KpOfferExpired(f"accept_offer:expired:{booking_id}")
        if not request.accept_terms:
            raise KpTermsNotAccepted(f"accept_offer:terms:{booking_id}")
        company_profile = await self._confirmed_company_profile(
            company_user.company_id, request.confirm_profile
        )
        accepted = await self.kp_repository.accept_offer(
            booking, company_profile, utc_now()
        )
        await notify_best_effort(self.notifier.booking_registered(accepted))
        return await self._build_booking_response(accepted)
