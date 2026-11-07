from app.models.kp_event import KpEventBooking, KpEventBoothZone, KpEventService
from app.schemas.kp import (
    BookingAdditionalServiceChargeResponse,
    BookingAdditionResponse,
    BookingResponse,
    BookingServiceResponse,
    BookingWithCompanyAndBoothZoneResponse,
    BoothZoneResponse,
    IncludedServiceResponse,
    PricedBookingBase,
    ServiceRequirementResponse,
    ServiceResponse,
    StaffBoothZoneResponse,
)
from app.services.booking_completeness import booking_completeness
from app.services.booth_zone_view import booth_zone_response, staff_booth_zone_response
from app.services.change_service import booking_changed_at
from app.services.kp_service.base import KpServiceBase
from app.services.pricing import booking_price


class ResponsesMixin(KpServiceBase):
    async def _build_booth_zone_response(
        self, zone: KpEventBoothZone
    ) -> BoothZoneResponse:
        return await booth_zone_response(zone, self.download_urls)

    async def _build_staff_booth_zone_response(
        self, zone: KpEventBoothZone
    ) -> StaffBoothZoneResponse:
        return await staff_booth_zone_response(zone, self.download_urls)

    async def _build_service_response(
        self, service: KpEventService, remaining_total_quantity: int | None = None
    ) -> ServiceResponse:
        return ServiceResponse(
            id=service.id,
            event_id=service.event_id,
            name=service.name,
            description=service.description,
            category=service.category,
            unit_label=service.unit_label,
            image_url=await self.download_urls.of(service.image_stored_file),
            confirmation_description=service.confirmation_description,
            order=service.order,
            price=service.price,
            max_quantity_per_booking=service.max_quantity_per_booking,
            max_total_quantity=service.max_total_quantity,
            remaining_total_quantity=remaining_total_quantity,
            is_active=service.is_active,
            included_services=[
                IncludedServiceResponse(
                    service_id=inclusion.included_service_id,
                    included_quantity=inclusion.included_quantity,
                )
                for inclusion in service.included_services
            ],
            excluded_service_ids=[
                exclusion.excluded_service_id for exclusion in service.excluded_services
            ],
            requirements=[
                ServiceRequirementResponse.model_validate(
                    requirement, from_attributes=True
                )
                for requirement in service.requirements
            ],
        )

    async def _booking_base(self, booking: KpEventBooking) -> PricedBookingBase:
        services = [
            BookingServiceResponse(
                id=booking_service.id,
                booking_id=booking_service.booking_id,
                service_id=booking_service.service_id,
                quantity=booking_service.quantity,
                included_quantity=booking_service.included_quantity,
                charged_quantity=booking_service.charged_quantity,
                unit_price=booking_service.service.price,
                line_net=booking_service.line_net,
                service=await self._build_service_response(booking_service.service),
            )
            for booking_service in booking.services
        ]
        additional_service_charges = [
            BookingAdditionalServiceChargeResponse(
                name=booking_service.service.name,
                quantity=booking_service.quantity,
                charged_quantity=booking_service.charged_quantity,
                line_net=booking_service.line_net,
            )
            for booking_service in booking.services
            if booking_service.charged_quantity > 0
        ]
        missing_items = booking_completeness(booking)
        return PricedBookingBase(
            id=booking.id,
            booking_number=booking.booking_number or 0,
            event_id=booking.event_id,
            company_id=booking.company_id,
            booth_zone_id=booking.booth_zone_id,
            booth_nr=booking.booth_nr,
            status=booking.status,
            status_changed_at=booking.status_changed_at,
            confirmed_at=booking.confirmed_at,
            rejection_reason=booking.rejection_reason,
            offer_deadline=booking.offer_deadline,
            missing_items=missing_items,
            is_complete=not missing_items,
            services=services,
            additional_service_charges=additional_service_charges,
            price=booking_price(booking, booking.event.vat_rate_permille),
        )

    async def _build_booking_response(self, booking: KpEventBooking) -> BookingResponse:
        base = await self._booking_base(booking)
        booth_zone_model = getattr(booking, "booth_zone", None)
        booth_zone = (
            await self._build_booth_zone_response(booth_zone_model)
            if booth_zone_model is not None
            else None
        )
        return BookingResponse(
            **dict(base), net_total=booking.total_price, booth_zone=booth_zone
        )

    async def _build_staff_booking_response(
        self, booking: KpEventBooking
    ) -> BookingWithCompanyAndBoothZoneResponse:
        base = await self._booking_base(booking)
        return BookingWithCompanyAndBoothZoneResponse(
            **dict(base),
            net_total=booking.total_price,
            company=booking.company,
            booth_zone=await self._build_staff_booth_zone_response(booking.booth_zone),
            booked_services_count=booking.booked_services_count,
            booked_services_summary=booking.booked_services_summary,
            nametag_count=booking.nametag_count,
            waitlist_count=booking.waitlist_count,
            company_details_submitted=booking.company_details_submitted,
            created_at=booking.created_at,
            changed_at=booking_changed_at(booking),
            status_note=booking.status_note,
            added_after_confirmation=[
                BookingAdditionResponse(
                    booking_service_id=booking_service.id,
                    quantity=min(
                        booking_service.added_after_confirmation,
                        booking_service.quantity,
                    ),
                )
                for booking_service in booking.services
                if booking_service.added_after_confirmation > 0
            ],
        )
