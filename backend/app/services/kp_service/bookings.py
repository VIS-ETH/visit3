from collections.abc import Sequence
from typing import Optional
from uuid import UUID

from app.core.auth_context import require_assigned_company_user
from app.core.exceptions import (
    CompanyNotConfirmed,
    CompanyNotFound,
    KpBookingAlreadyExists,
    KpBookingZoneSwitchNotAllowed,
    KpBoothZoneFull,
    KpRegistrationClosed,
)
from app.models.kp_event import KpBookingStatus, KpEvent
from app.schemas.kp import (
    BookingResponse,
    BookingServiceInput,
    CreateBookingInput,
    MyBookingResponse,
)
from app.services.booking_notifier import notify_best_effort
from app.services.event_lookup import require_locked_event
from app.services.kp_service.quantities import (
    ServiceQuantitiesMixin,
    booked_quantities,
    requested_quantities,
    stored_quantities,
    zone_included_quantities,
)
from app.services.kp_service.responses import ResponsesMixin


class BookingsMixin(ResponsesMixin, ServiceQuantitiesMixin):
    async def _ensure_registration_open(self, event: KpEvent, company_id: UUID) -> None:
        if not await self._is_registration_open(event, company_id):
            raise KpRegistrationClosed(
                f"register_booking:closed:{event.id}:{company_id}"
            )

    async def _ensure_company_confirmed(self, company_id: UUID) -> None:
        company = await self.kp_repository.get_company(company_id)
        if company is None:
            raise CompanyNotFound(f"register_booking:{company_id}")
        if company.confirmed_at is None:
            raise CompanyNotConfirmed(f"register_booking:{company_id}")

    async def register_booking(
        self,
        event_id: UUID,
        booth_zone_id: UUID,
        services: Sequence[BookingServiceInput] = (),
        confirm_profile: bool = False,
    ) -> BookingResponse:
        company_user = require_assigned_company_user(self.current_user)
        event = await self._get_event(event_id)
        await self._ensure_registration_open(event, company_user.company_id)
        await self._ensure_company_confirmed(company_user.company_id)
        company_profile = await self._confirmed_company_profile(
            company_user.company_id, confirm_profile
        )

        await require_locked_event(
            self.kp_repository,
            event_id,
            f"register_booking:locked_event_not_found:{event_id}",
        )
        await self._get_event_booth_zone(booth_zone_id, event_id, "register_booking")

        existing = await self.kp_repository.get_company_active_booking_for_event(
            event_id, company_user.company_id
        )
        if existing is not None:
            raise KpBookingAlreadyExists(
                f"register_booking:already_exists:{event_id}:{company_user.company_id}"
            )

        locked_zone = await self._lock_zone_until_booking_is_inserted(booth_zone_id)
        await self._ensure_zone_registration_open(
            locked_zone, company_user.company_id, "register_booking"
        )
        await self._ensure_zone_not_full(event_id, locked_zone, "register_booking")

        zone_quantities = zone_included_quantities(locked_zone)
        requested = requested_quantities(services)
        included_quantities = await self._with_package_inclusions(
            zone_quantities, requested
        )
        validated_services = await self._validate_booking_services(
            event_id, services, included_quantities=included_quantities
        )
        await self._ensure_services_combinable(
            stored_quantities(requested, included_quantities),
            zone_quantities,
            "register_booking",
        )
        booking = await self.kp_repository.create_booking(
            event_id=event_id,
            company_id=company_user.company_id,
            booth_zone_id=booth_zone_id,
            create_booking_input=CreateBookingInput(status=KpBookingStatus.REGISTERED),
            services=validated_services,
            included_quantities=zone_quantities,
            company_profile=company_profile,
        )
        await notify_best_effort(self.notifier.booking_registered(booking))
        return await self._build_booking_response(booking)

    async def add_booking_services(
        self,
        booking_id: UUID,
        services: Sequence[BookingServiceInput],
    ) -> BookingResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "add_booking_services"
        )
        self._ensure_booking_editable_by_company(booking, "add_booking_services")

        await require_locked_event(
            self.kp_repository,
            booking.event_id,
            f"add_booking_services:locked_event_not_found:{booking.event_id}",
        )
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "add_booking_services", lock=True
        )
        self._ensure_booking_editable_by_company(booking, "add_booking_services")

        existing_quantities = booked_quantities(booking)
        zone_quantities = await self.kp_repository.zone_inclusion_portion(booking.id)
        totals = dict(existing_quantities)
        for service_id, quantity in requested_quantities(services).items():
            totals[service_id] = totals.get(service_id, 0) + quantity
        included_quantities = await self._with_package_inclusions(
            zone_quantities, totals
        )
        validated_services = await self._validate_booking_services(
            booking.event_id,
            services,
            existing_quantities=existing_quantities,
            included_quantities=included_quantities,
        )
        await self._ensure_services_combinable(
            stored_quantities(totals, included_quantities),
            zone_quantities,
            "add_booking_services",
        )
        updated = await self.kp_repository.add_booking_services(
            booking,
            validated_services,
            after_confirmation=booking.status == KpBookingStatus.CONFIRMED,
        )
        return await self._build_booking_response(updated)

    async def get_my_booking(self, event_id: UUID) -> Optional[MyBookingResponse]:
        company_user = require_assigned_company_user(self.current_user)
        event = await self._get_event(event_id)
        company_id = company_user.company_id
        active = await self.kp_repository.get_company_active_booking_for_event(
            event_id, company_id
        )
        booking = active or (
            await self.kp_repository.get_company_latest_inactive_booking_for_event(
                event_id, company_id
            )
        )
        if booking is None:
            return None
        can_register = active is None and await self._is_registration_open(
            event, company_id
        )
        response = await self._build_booking_response(booking)
        return MyBookingResponse(**response.model_dump(), can_register=can_register)

    async def switch_booking_zone(
        self, booking_id: UUID, booth_zone_id: UUID
    ) -> BookingResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "switch_booking_zone"
        )
        await require_locked_event(
            self.kp_repository,
            booking.event_id,
            f"switch_booking_zone:locked_event_not_found:{booking.event_id}",
        )
        await self._get_event_booth_zone(
            booth_zone_id, booking.event_id, "switch_booking_zone"
        )
        locked_zone = await self._lock_zone_until_booking_is_inserted(
            booth_zone_id, "switch_booking_zone"
        )
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "switch_booking_zone", lock=True
        )
        self._ensure_zone_unlocked(booking, "switch_booking_zone")
        if booking.status != KpBookingStatus.REGISTERED:
            raise KpBookingZoneSwitchNotAllowed(
                f"switch_booking_zone:status:{booking_id}:{booking.status}"
            )
        self._ensure_finalization_deadline_open(booking, "switch_booking_zone")
        if booth_zone_id == booking.booth_zone_id:
            raise KpBookingZoneSwitchNotAllowed(
                f"switch_booking_zone:same_zone:{booking_id}:{booth_zone_id}"
            )
        await self._ensure_zone_registration_open(
            locked_zone, company_user.company_id, "switch_booking_zone"
        )
        count = await self.kp_repository.count_active_bookings_for_zone(
            booking.event_id, booth_zone_id
        )
        if count >= locked_zone.capacity:
            raise KpBoothZoneFull(f"switch_booking_zone:full:{booth_zone_id}")

        await self._ensure_zone_switch_stock(
            booking, locked_zone, "switch_booking_zone"
        )

        left_booth_zone_id = booking.booth_zone_id
        switched = await self.kp_repository.move_booking_to_zone(
            booking, locked_zone, clear_whole_waitlist=False
        )
        await self._promote_waitlist(switched.event_id, left_booth_zone_id)
        return await self._build_booking_response(switched)
