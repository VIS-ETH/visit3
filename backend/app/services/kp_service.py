from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from app.core.auth_context import (
    require_assigned_company_user,
    require_confirmed_company_user,
    require_kp_president_user,
    require_staff_user,
)
from app.core.config import get_settings
from app.core.exceptions import (
    KpAdvertisementServiceInvalid,
    KpBookingAlreadyExists,
    KpBookingConfirmationRequiresFinalized,
    KpBookingConfirmedReadonly,
    KpBookingNotFound,
    KpBookingNotOwned,
    KpBookingStatusTransitionInvalid,
    KpBoothZoneAtCapacity,
    KpBoothZoneEventMismatch,
    KpBoothZoneNotFound,
    KpEventNotFound,
    KpIndustryNameExists,
    KpIndustryNotFound,
    KpNameExists,
    KpRegistrationClosed,
    KpRequirementBookingServiceMismatch,
    KpRequirementFileUploadNotAllowed,
    KpRequirementTextAnswerNotAllowed,
    KpServiceNotFound,
    KpServiceQuantityInvalid,
    KpServiceRequirementNotFound,
    KpServiceUnavailable,
    KpWaitlistSameZone,
)
from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventService,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
    KpIndustry,
)
from app.models.user import User
from app.repositories.kp_repository import KpRepository
from app.schemas.kp import (
    BookingAdditionalServiceChargeResponse,
    BookingRequirementFileMapResponse,
    BookingResponse,
    BookingServiceInput,
    BookingServiceResponse,
    BookingWithCompanyAndBoothZoneResponse,
    BoothZoneResponse,
    BoothZoneWithAvailabilityResult,
    CloneKpInput,
    CompanyDetailsResponse,
    CreateBookingInput,
    CreateBoothZoneInput,
    CreateIndustryInput,
    CreateKpInput,
    CreateServiceInput,
    IndustryResponse,
    RequirementFileResponse,
    RequirementTextResponse,
    ServiceRequirementResponse,
    ServiceResponse,
    StoredFileResponse,
    UpdateBookingBoothNumberInput,
    UpdateBookingInput,
    UpdateBookingStatusInput,
    UpdateBoothZoneInput,
    UpdateKpInput,
    UpdateServiceInput,
    UpsertCompanyDetailsInput,
)
from app.services.attachment_utils import (
    delete_attached_file,
    upload_and_replace_attached_file,
)
from app.services.kp_helpers import get_event_or_raise
from app.services.storage_service import StorageService


class KpService:
    def __init__(
        self,
        kp_repository: KpRepository,
        storage_service: StorageService,
        current_user: User,
    ) -> None:
        self.kp_repository = kp_repository
        self.storage_service = storage_service
        self.current_user = current_user
        self.settings = get_settings()

    async def _get_event(self, event_id: UUID) -> KpEvent:
        return await get_event_or_raise(self.kp_repository, event_id, context="event")

    async def list_kps(self) -> Sequence[KpEvent]:
        return await self.kp_repository.list_kps()

    async def get_latest_kp(self) -> Optional[KpEvent]:
        return await self.kp_repository.get_latest_kp()

    async def get_event_by_id(self, event_id: UUID) -> KpEvent:
        return await self._get_event(event_id)

    async def clone_kp(self, event_id: UUID, clone_kp_input: CloneKpInput) -> KpEvent:
        require_kp_president_user(self.current_user)
        existing = await self.kp_repository.get_by_name(clone_kp_input.name)
        if existing is not None:
            raise KpNameExists(f"clone_kp:{clone_kp_input.name}")

        cloned_event = await self.kp_repository.clone_kp(event_id, clone_kp_input)
        if cloned_event is None:
            raise KpEventNotFound(f"event:not_found:{event_id}")
        return cloned_event

    async def update_kp(
        self, event_id: UUID, update_kp_input: UpdateKpInput
    ) -> KpEvent:
        require_kp_president_user(self.current_user)
        updates = update_kp_input.model_dump(exclude_unset=True)
        event = await self._get_event(event_id)
        new_name = updates.get("name")
        if new_name is not None and new_name != event.name:
            existing = await self.kp_repository.get_by_name(new_name)
            if existing is not None:
                raise KpNameExists(f"update_kp:{new_name}")
        return await self.kp_repository.update_kp(
            event=event, update_kp_input=update_kp_input
        )

    async def set_advertisement_service(
        self, event_id: UUID, service_id: UUID | None
    ) -> KpEvent:
        require_kp_president_user(self.current_user)
        event = await self._get_event(event_id)
        if service_id is None:
            return await self.kp_repository.set_advertisement_service_id(event, None)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"advertisement_service:not_found:{service_id}")
        self._validate_advertisement_service(event_id, service)
        return await self.kp_repository.set_advertisement_service_id(event, service_id)

    def _validate_advertisement_service(
        self, event_id: UUID, service: KpEventService
    ) -> None:
        if service.event_id != event_id:
            raise KpAdvertisementServiceInvalid(
                f"advertisement_service:event_mismatch:{service.id}"
            )
        pdf_requirements = [
            requirement
            for requirement in service.requirements
            if requirement.type == KpEventServiceRequirementType.PDF_SINGLE_PAGE
        ]
        if len(pdf_requirements) != 1:
            raise KpAdvertisementServiceInvalid(
                f"advertisement_service:requirement_count:{service.id}:{len(pdf_requirements)}"
            )
        if len(service.requirements) != 1:
            raise KpAdvertisementServiceInvalid(
                f"advertisement_service:extra_requirements:{service.id}"
            )
        if service.max_quantity_per_booking != 1:
            raise KpAdvertisementServiceInvalid(
                f"advertisement_service:max_quantity:{service.id}"
            )

    # --- Booth Zones ---

    async def list_booth_zones(self, event_id: UUID) -> Sequence[KpEventBoothZone]:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        return await self.kp_repository.list_booth_zones(event_id)

    async def create_booth_zone(
        self, event_id: UUID, create_booth_zone_input: CreateBoothZoneInput
    ) -> KpEventBoothZone:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        return await self.kp_repository.create_booth_zone(
            event_id, create_booth_zone_input
        )

    async def update_booth_zone(
        self, booth_zone_id: UUID, update_booth_zone_input: UpdateBoothZoneInput
    ) -> KpEventBoothZone:
        require_kp_president_user(self.current_user)
        zone = await self.kp_repository.get_booth_zone_by_id(booth_zone_id)
        if zone is None:
            raise KpBoothZoneNotFound(f"booth_zone:not_found:{booth_zone_id}")
        return await self.kp_repository.update_booth_zone(zone, update_booth_zone_input)

    async def delete_booth_zone(self, booth_zone_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        zone = await self.kp_repository.get_booth_zone_by_id(booth_zone_id)
        if zone is None:
            raise KpBoothZoneNotFound(f"booth_zone:not_found:{booth_zone_id}")
        await self.kp_repository.delete_booth_zone(zone)

    # --- Services ---

    async def _service_image_url(self, service: KpEventService) -> str | None:
        stored_file = service.image_stored_file
        if stored_file is None:
            return None
        return await self.storage_service.generate_download_url(
            stored_file.storage_key, stored_file.original_filename
        )

    async def _build_service_response(self, service: KpEventService) -> ServiceResponse:
        return ServiceResponse(
            id=service.id,
            event_id=service.event_id,
            name=service.name,
            description=service.description,
            image_url=await self._service_image_url(service),
            confirmation_description=service.confirmation_description,
            order=service.order,
            price=service.price,
            max_quantity_per_booking=service.max_quantity_per_booking,
            max_total_quantity=service.max_total_quantity,
            is_active=service.is_active,
            requirements=[
                ServiceRequirementResponse.model_validate(
                    requirement, from_attributes=True
                )
                for requirement in service.requirements
            ],
        )

    async def list_services(self, event_id: UUID) -> list[ServiceResponse]:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        services = await self.kp_repository.list_services(event_id)
        return [await self._build_service_response(service) for service in services]

    async def list_available_services_for_company(
        self, event_id: UUID
    ) -> list[ServiceResponse]:
        require_confirmed_company_user(self.current_user)
        await self._get_event(event_id)
        services = await self.kp_repository.list_services(event_id)
        return [
            await self._build_service_response(service)
            for service in services
            if service.is_active
        ]

    async def create_service(
        self, event_id: UUID, create_service_input: CreateServiceInput
    ) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        service = await self.kp_repository.create_service(
            event_id, create_service_input
        )
        return await self._build_service_response(service)

    async def update_service(
        self, service_id: UUID, update_service_input: UpdateServiceInput
    ) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        updated = await self.kp_repository.update_service(service, update_service_input)
        return await self._build_service_response(updated)

    async def delete_service(self, service_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        old_storage_key = (
            service.image_stored_file.storage_key
            if service.image_stored_file is not None
            else None
        )
        old_stored_file = service.image_stored_file
        await self.kp_repository.delete_service(service)
        if old_storage_key is not None:
            await self.storage_service.delete_object(old_storage_key)
        if old_stored_file is not None:
            await self.kp_repository.delete_stored_file(old_stored_file)

    async def upload_service_image(
        self,
        service_id: UUID,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        mime_type = self.storage_service.validate_image_file(
            filename,
            content,
            content_type,
            error_context=f"service_image:{service_id}",
        )
        old_stored_file = service.image_stored_file
        suffix = Path(filename).suffix
        storage_key = f"kp/services/{service_id}/image/{uuid4()}{suffix}"
        _, updated = await upload_and_replace_attached_file(
            storage_service=self.storage_service,
            kp_repository=self.kp_repository,
            filename=filename,
            content=content,
            content_type=mime_type,
            storage_key=storage_key,
            old_stored_file=old_stored_file,
            attach=lambda stored_file: self.kp_repository.set_service_image_stored_file_id(
                service, stored_file.id
            ),
        )
        return await self._build_service_response(updated)

    async def delete_service_image(self, service_id: UUID) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        stored_file = service.image_stored_file
        if stored_file is None:
            return await self._build_service_response(service)
        updated = await delete_attached_file(
            storage_service=self.storage_service,
            kp_repository=self.kp_repository,
            old_stored_file=stored_file,
            detach=lambda: self.kp_repository.set_service_image_stored_file_id(
                service, None
            ),
        )
        return await self._build_service_response(updated)

    # --- Industries ---

    async def list_industries(self) -> Sequence[KpIndustry]:
        if self.current_user.is_staff or self.current_user.is_admin:
            pass
        else:
            require_confirmed_company_user(self.current_user)
        return await self.kp_repository.list_industries()

    async def create_industry(
        self, create_industry_input: CreateIndustryInput
    ) -> KpIndustry:
        require_kp_president_user(self.current_user)
        existing = await self.kp_repository.get_industry_by_name(
            create_industry_input.name
        )
        if existing is not None:
            raise KpIndustryNameExists(f"create_industry:{create_industry_input.name}")
        return await self.kp_repository.create_industry(create_industry_input)

    async def delete_industry(self, industry_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        industry = await self.kp_repository.get_industry_by_id(industry_id)
        if industry is None:
            raise KpIndustryNotFound(f"industry:not_found:{industry_id}")
        await self.kp_repository.delete_industry(industry)

    # --- Company Booking Flow ---

    async def _ensure_registration_open(self, event: KpEvent, company_id: UUID) -> None:
        if event.is_registration_open():
            return
        exception = await self.kp_repository.get_registration_exception(
            event.id, company_id
        )
        if exception is not None and exception.allowed_until >= date.today():
            return
        raise KpRegistrationClosed(f"register_booking:closed:{event.id}:{company_id}")

    async def list_booth_zones_for_company(
        self, event_id: UUID
    ) -> list[BoothZoneWithAvailabilityResult]:
        require_confirmed_company_user(self.current_user)
        await self._get_event(event_id)
        zones = await self.kp_repository.list_booth_zones(event_id)
        result: list[BoothZoneWithAvailabilityResult] = []
        for zone in zones:
            count = await self.kp_repository.count_active_bookings_for_zone(
                event_id, zone.id
            )
            available = max(zone.capacity - count, 0)
            result.append(
                BoothZoneWithAvailabilityResult(
                    **zone.model_dump(),
                    available_spots=available,
                )
            )
        return result

    async def _validate_booking_services(
        self,
        event_id: UUID,
        services: Sequence[BookingServiceInput],
        existing_quantities: dict[UUID, int] | None = None,
    ) -> list[BookingServiceInput]:
        existing_quantities = existing_quantities or {}
        service_quantities: dict[UUID, int] = {}
        for booking_service in services:
            service_quantities[booking_service.service_id] = (
                service_quantities.get(booking_service.service_id, 0)
                + booking_service.quantity
            )

        validated_services: list[BookingServiceInput] = []
        for service_id, quantity in service_quantities.items():
            service = await self.kp_repository.lock_model_by_id(
                KpEventService, service_id
            )
            if service is None:
                raise KpServiceNotFound(
                    f"register_booking:service_not_found:{service_id}"
                )
            if service.event_id != event_id or not service.is_active:
                raise KpServiceUnavailable(
                    f"register_booking:service_unavailable:{service_id}"
                )
            total_booking_quantity = existing_quantities.get(service_id, 0) + quantity
            if total_booking_quantity > service.max_quantity_per_booking:
                raise KpServiceQuantityInvalid(
                    "booking_service:service_max_per_booking:"
                    f"{service_id}:{total_booking_quantity}"
                )
            if service.max_total_quantity > 0:
                booked_quantity = (
                    await self.kp_repository.count_active_service_quantity(service_id)
                )
                if booked_quantity + quantity > service.max_total_quantity:
                    raise KpServiceQuantityInvalid(
                        f"register_booking:service_max_total:{service_id}:{quantity}"
                    )
            validated_services.append(
                BookingServiceInput(service_id=service_id, quantity=quantity)
            )
        return validated_services

    def _ensure_booking_editable_by_company(
        self, booking: KpEventBooking, context: str
    ) -> None:
        if booking.status in {KpBookingStatus.CONFIRMED, KpBookingStatus.CANCELLED}:
            raise KpBookingConfirmedReadonly(
                f"{context}:readonly:{booking.id}:{booking.status}"
            )

    async def _company_details_to_response(
        self, details: KpBookingCompanyDetails
    ) -> CompanyDetailsResponse:
        industries = [
            IndustryResponse.model_validate(link.industry, from_attributes=True)
            for link in details.industry_links
        ]
        logo_url: str | None = None
        if details.logo_stored_file is not None:
            logo_url = await self.storage_service.generate_download_url(
                details.logo_stored_file.storage_key,
                details.logo_stored_file.original_filename,
            )
        return CompanyDetailsResponse(
            id=details.id,
            booking_id=details.booking_id,
            profile=details.profile,
            brand_name=details.brand_name,
            address=details.address,
            contact_person=details.contact_person,
            places_of_work=details.places_of_work,
            website=details.website,
            employees_count=details.employees_count,
            employees_count_switzerland=details.employees_count_switzerland,
            vacancies_worldwide=details.vacancies_worldwide,
            vacancies_switzerland=details.vacancies_switzerland,
            annual_revenue_chf_millions=details.annual_revenue_chf_millions,
            offer_internship=details.offer_internship,
            offer_part_time=details.offer_part_time,
            offer_thesis=details.offer_thesis,
            languages=details.languages,
            industries=industries,
            industry_ids=[industry.id for industry in industries],
            logo_url=logo_url,
        )

    async def _build_company_details_response(
        self, booking: KpEventBooking
    ) -> CompanyDetailsResponse | None:
        details = booking.company_details
        if details is None:
            return None
        return await self._company_details_to_response(details)

    async def _build_booking_response(self, booking: KpEventBooking) -> BookingResponse:
        services, additional_service_charges = await self._build_booking_services(
            booking
        )
        booth_zone_model = getattr(booking, "booth_zone", None)
        booth_zone = (
            BoothZoneResponse.model_validate(booth_zone_model, from_attributes=True)
            if booth_zone_model is not None
            else None
        )
        return BookingResponse(
            id=booking.id,
            booking_number=booking.booking_number or 0,
            event_id=booking.event_id,
            company_id=booking.company_id,
            booth_zone_id=booking.booth_zone_id,
            booth_nr=booking.booth_nr,
            status=booking.status,
            booth_zone=booth_zone,
            services=services,
            additional_service_charges=additional_service_charges,
            total_price=self._booking_total_price(booking),
            company_details=await self._build_company_details_response(booking),
        )

    def _booking_total_price(self, booking: KpEventBooking) -> int:
        booth_zone = getattr(booking, "booth_zone", None)
        base_price = booth_zone.base_price if booth_zone is not None else 0
        return base_price + sum(
            booking_service.charged_quantity * booking_service.service.price
            for booking_service in booking.services
        )

    async def _build_booking_services(
        self, booking: KpEventBooking
    ) -> tuple[
        list[BookingServiceResponse],
        list[BookingAdditionalServiceChargeResponse],
    ]:
        service_responses = [
            BookingServiceResponse(
                id=booking_service.id,
                booking_id=booking_service.booking_id,
                service_id=booking_service.service_id,
                quantity=booking_service.quantity,
                included_quantity=booking_service.included_quantity,
                service=await self._build_service_response(booking_service.service),
            )
            for booking_service in booking.services
        ]
        additional_service_charges = [
            BookingAdditionalServiceChargeResponse(
                name=booking_service.service.name,
                quantity=booking_service.quantity,
                charged_quantity=booking_service.charged_quantity,
                line_total_cents=booking_service.charged_quantity
                * booking_service.service.price,
            )
            for booking_service in booking.services
            if booking_service.charged_quantity > 0
        ]
        return service_responses, additional_service_charges

    async def _build_staff_booking_response(
        self, booking: KpEventBooking
    ) -> BookingWithCompanyAndBoothZoneResponse:
        services, additional_service_charges = await self._build_booking_services(
            booking
        )
        booth_zone = BoothZoneResponse.model_validate(
            booking.booth_zone, from_attributes=True
        )
        return BookingWithCompanyAndBoothZoneResponse(
            id=booking.id,
            booking_number=booking.booking_number or 0,
            event_id=booking.event_id,
            company_id=booking.company_id,
            booth_zone_id=booking.booth_zone_id,
            booth_nr=booking.booth_nr,
            status=booking.status,
            company=booking.company,
            booth_zone=booth_zone,
            services=services,
            additional_service_charges=additional_service_charges,
            total_price=self._booking_total_price(booking),
            booked_services_count=booking.booked_services_count,
            booked_services_summary=booking.booked_services_summary,
            nametag_count=booking.nametag_count,
            waitlist_count=booking.waitlist_count,
            company_details_submitted=booking.company_details_submitted,
            company_details=await self._build_company_details_response(booking),
        )

    async def register_booking(
        self,
        event_id: UUID,
        booth_zone_id: UUID,
        services: Sequence[BookingServiceInput] = (),
    ) -> BookingResponse:
        company_user = require_assigned_company_user(self.current_user)
        event = await self._get_event(event_id)
        await self._ensure_registration_open(event, company_user.company_id)

        locked_event = await self.kp_repository.lock_model_by_id(KpEvent, event_id)
        if locked_event is None:
            raise KpEventNotFound(f"register_booking:locked_event_not_found:{event_id}")

        zone = await self.kp_repository.get_booth_zone_by_id(booth_zone_id)
        if zone is None:
            raise KpBoothZoneNotFound(
                f"register_booking:zone_not_found:{booth_zone_id}"
            )
        if zone.event_id != event_id:
            raise KpBoothZoneEventMismatch(
                f"register_booking:zone_event_mismatch:{booth_zone_id}"
            )

        existing = await self.kp_repository.get_company_active_booking_for_event(
            event_id, company_user.company_id
        )
        if existing is not None:
            raise KpBookingAlreadyExists(
                f"register_booking:already_exists:{event_id}:{company_user.company_id}"
            )

        # Acquire a row-level lock on the zone before counting, so that the
        # count check and the insert are serialised across concurrent requests.
        locked_zone = await self.kp_repository.lock_model_by_id(
            KpEventBoothZone, booth_zone_id
        )
        if locked_zone is None:
            raise KpBoothZoneNotFound(
                f"register_booking:locked_zone_not_found:{booth_zone_id}"
            )

        count = await self.kp_repository.count_active_bookings_for_zone(
            event_id, booth_zone_id
        )
        if count >= locked_zone.capacity:
            raise KpBoothZoneAtCapacity(f"register_booking:at_capacity:{booth_zone_id}")

        validated_services = await self._validate_booking_services(event_id, services)
        booking = await self.kp_repository.create_booking(
            event_id=event_id,
            company_id=company_user.company_id,
            booth_zone_id=booth_zone_id,
            create_booking_input=CreateBookingInput(status=KpBookingStatus.REGISTERED),
            services=validated_services,
            included_services=locked_zone.included_services,
        )
        return await self._build_booking_response(booking)

    async def add_booking_services(
        self,
        booking_id: UUID,
        services: Sequence[BookingServiceInput],
    ) -> BookingResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(booking_id, company_user.company_id)
        self._ensure_booking_editable_by_company(booking, "add_booking_services")

        existing_quantities = {
            booking_service.service_id: booking_service.quantity
            for booking_service in booking.services
        }
        validated_services = await self._validate_booking_services(
            booking.event_id,
            services,
            existing_quantities=existing_quantities,
        )
        updated = await self.kp_repository.add_booking_services(
            booking,
            validated_services,
        )
        return await self._build_booking_response(updated)

    async def get_my_booking(self, event_id: UUID) -> Optional[BookingResponse]:
        company_user = require_assigned_company_user(self.current_user)
        await self._get_event(event_id)
        booking = await self.kp_repository.get_company_active_booking_for_event(
            event_id, company_user.company_id
        )
        if booking is None:
            return None
        return await self._build_booking_response(booking)

    # --- Bookings ---

    async def list_bookings_for_event(
        self, event_id: UUID
    ) -> list[BookingWithCompanyAndBoothZoneResponse]:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        bookings = await self.kp_repository.list_bookings_for_event(event_id)
        return [
            await self._build_staff_booking_response(booking) for booking in bookings
        ]

    async def get_event_booking(
        self, event_id: UUID, booking_id: UUID
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        booking = await self._get_booking(booking_id)
        if booking.event_id != event_id:
            raise KpBookingNotFound(f"booking:event_mismatch:{event_id}:{booking_id}")
        return await self._build_staff_booking_response(booking)

    async def _get_owned_booking(
        self, booking_id: UUID, company_id: UUID
    ) -> KpEventBooking:
        booking = await self.kp_repository.get_booking_by_id(booking_id)
        if booking is None:
            raise KpBookingNotFound(f"booking_upgrade_waitlist:not_found:{booking_id}")
        if booking.company_id != company_id:
            raise KpBookingNotOwned(f"booking_upgrade_waitlist:not_owned:{booking_id}")
        return booking

    async def _get_booking(self, booking_id: UUID) -> KpEventBooking:
        booking = await self.kp_repository.get_booking_by_id(booking_id)
        if booking is None:
            raise KpBookingNotFound(f"booking:not_found:{booking_id}")
        return booking

    async def _get_owned_booking_service(
        self, booking_service_id: UUID, company_id: UUID
    ) -> KpEventBookingService:
        booking_service = await self._get_booking_service(booking_service_id)
        if booking_service.booking.company_id != company_id:
            raise KpBookingNotOwned(f"booking_service:not_owned:{booking_service_id}")
        return booking_service

    async def _get_booking_service(
        self, booking_service_id: UUID
    ) -> KpEventBookingService:
        booking_service = await self.kp_repository.get_booking_service_by_id(
            booking_service_id
        )
        if booking_service is None:
            raise KpBookingNotFound(f"booking_service:not_found:{booking_service_id}")
        return booking_service

    def _ensure_company_status_transition(
        self, booking: KpEventBooking, next_status: KpBookingStatus
    ) -> None:
        if booking.status == next_status:
            return
        allowed_transitions: dict[KpBookingStatus, set[KpBookingStatus]] = {
            KpBookingStatus.DRAFT: {
                KpBookingStatus.REGISTERED,
                KpBookingStatus.CANCELLED,
            },
            KpBookingStatus.REGISTERED: {
                KpBookingStatus.FINALIZED,
                KpBookingStatus.CANCELLED,
            },
            KpBookingStatus.FINALIZED: {KpBookingStatus.CANCELLED},
            KpBookingStatus.CONFIRMED: set(),
            KpBookingStatus.CANCELLED: set(),
        }
        if next_status not in allowed_transitions.get(booking.status, set()):
            raise KpBookingStatusTransitionInvalid(
                f"booking_status_transition:{booking.id}:{booking.status}->{next_status}"
            )

    async def list_booking_upgrade_waitlist(
        self, booking_id: UUID
    ) -> Sequence[KpEventBookingUpgradeWaitlist]:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(booking_id, company_user.company_id)
        return await self.kp_repository.list_booking_upgrade_waitlist_entries(
            booking.id
        )

    async def replace_booking_upgrade_waitlist(
        self, booking_id: UUID, target_booth_zone_ids: list[UUID]
    ) -> Sequence[KpEventBookingUpgradeWaitlist]:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(booking_id, company_user.company_id)

        unique_target_ids = list(dict.fromkeys(target_booth_zone_ids))
        for target_booth_zone_id in unique_target_ids:
            target_zone = await self.kp_repository.get_booth_zone_by_id(
                target_booth_zone_id
            )
            if target_zone is None:
                raise KpBoothZoneNotFound(
                    f"booking_upgrade_waitlist:zone_not_found:{target_booth_zone_id}"
                )
            if target_zone.event_id != booking.event_id:
                raise KpBoothZoneEventMismatch(
                    f"booking_upgrade_waitlist:zone_event_mismatch:{target_booth_zone_id}"
                )
            if target_zone.id == booking.booth_zone_id:
                raise KpWaitlistSameZone(
                    f"booking_upgrade_waitlist:same_zone:{booking_id}:{target_zone.id}"
                )

        return await self.kp_repository.replace_booking_upgrade_waitlist_entries(
            booking=booking,
            target_booth_zone_ids=unique_target_ids,
        )

    async def get_booking_company_details(
        self, booking_id: UUID
    ) -> CompanyDetailsResponse | None:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(booking_id, company_user.company_id)
        details = await self.kp_repository.get_company_details_by_booking_id(booking.id)
        if details is None:
            return None
        return await self._company_details_to_response(details)

    async def upsert_booking_company_details(
        self,
        booking_id: UUID,
        upsert_company_details_input: UpsertCompanyDetailsInput,
    ) -> CompanyDetailsResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(booking_id, company_user.company_id)
        self._ensure_booking_editable_by_company(
            booking, "upsert_booking_company_details"
        )

        industry_ids = list(
            dict.fromkeys(upsert_company_details_input.industry_ids or [])
        )
        industries = await self.kp_repository.list_industries_by_ids(industry_ids)
        if len(industries) != len(industry_ids):
            found_ids = {industry.id for industry in industries}
            missing_ids = [
                industry_id
                for industry_id in industry_ids
                if industry_id not in found_ids
            ]
            raise KpIndustryNotFound(
                f"booking_company_details:industry_not_found:{missing_ids[0]}"
            )

        details = await self.kp_repository.upsert_company_details(
            booking.id,
            upsert_company_details_input,
            industry_ids,
        )
        return await self._company_details_to_response(details)

    async def update_my_booking_status(
        self, booking_id: UUID, update_booking_input: UpdateBookingStatusInput
    ) -> BookingWithCompanyAndBoothZoneResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(booking_id, company_user.company_id)
        self._ensure_company_status_transition(booking, update_booking_input.status)
        updated = await self.kp_repository.update_booking(
            booking, UpdateBookingInput(status=update_booking_input.status)
        )
        return await self._build_staff_booking_response(updated)

    async def update_booking_booth_number(
        self, booking_id: UUID, update_booking_input: UpdateBookingBoothNumberInput
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_kp_president_user(self.current_user)
        booking = await self._get_booking(booking_id)
        updated = await self.kp_repository.update_booking(
            booking, UpdateBookingInput(booth_nr=update_booking_input.booth_nr)
        )
        return await self._build_staff_booking_response(updated)

    async def confirm_booking(
        self, booking_id: UUID
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_kp_president_user(self.current_user)
        booking = await self._get_booking(booking_id)
        if booking.status != KpBookingStatus.FINALIZED:
            raise KpBookingConfirmationRequiresFinalized(
                f"booking_confirm:not_finalized:{booking_id}:{booking.status}"
            )
        updated = await self.kp_repository.update_booking(
            booking, UpdateBookingInput(status=KpBookingStatus.CONFIRMED)
        )
        return await self._build_staff_booking_response(updated)

    async def _get_requirement_for_booking_service(
        self, booking_service: KpEventBookingService, requirement_id: UUID
    ) -> KpEventServiceRequirement:
        requirement = await self.kp_repository.get_service_requirement_by_id(
            requirement_id
        )
        if requirement is None:
            raise KpServiceRequirementNotFound(
                f"booking_requirement:not_found:{requirement_id}"
            )

        if requirement.service_id != booking_service.service_id:
            raise KpRequirementBookingServiceMismatch(
                f"booking_requirement:service_mismatch:{booking_service.id}:{requirement_id}"
            )
        return requirement

    def _validate_requirement_upload(
        self,
        requirement: KpEventServiceRequirement,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> str:
        if requirement.type == KpEventServiceRequirementType.TEXT:
            raise KpRequirementFileUploadNotAllowed(
                f"booking_requirement:not_file_upload:{requirement.id}"
            )

        error_context = f"booking_requirement:{requirement.type.value}:{requirement.id}"
        if requirement.type == KpEventServiceRequirementType.IMAGE:
            return self.storage_service.validate_image_file(
                filename, content, content_type, error_context=error_context
            )

        if requirement.type == KpEventServiceRequirementType.PDF:
            return self.storage_service.validate_pdf_file(
                filename, content, content_type, error_context=error_context
            )

        if requirement.type == KpEventServiceRequirementType.PDF_SINGLE_PAGE:
            return self.storage_service.validate_single_page_pdf_file(
                filename, content, content_type, error_context=error_context
            )

        if requirement.type == KpEventServiceRequirementType.VIDEO:
            return self.storage_service.validate_video_file(
                filename, content, content_type, error_context=error_context
            )

        return self.storage_service.validate_generic_file(
            filename, content, content_type, error_context=error_context
        )

    async def upload_booking_requirement_file(
        self,
        booking_service_id: UUID,
        requirement_id: UUID,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> KpEventBookingServiceFileLink:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        self._ensure_booking_editable_by_company(
            booking_service.booking, "upload_booking_requirement_file"
        )
        requirement = await self._get_requirement_for_booking_service(
            booking_service, requirement_id
        )
        mime_type = self._validate_requirement_upload(
            requirement, filename, content, content_type
        )
        suffix = Path(filename).suffix
        storage_key = f"kp/booking-services/{booking_service.id}/requirements/{requirement.id}/{uuid4()}{suffix}"
        existing_file = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement.id
        )
        old_stored_file = (
            existing_file.stored_file if existing_file is not None else None
        )
        _, requirement_file = await upload_and_replace_attached_file(
            storage_service=self.storage_service,
            kp_repository=self.kp_repository,
            filename=filename,
            content=content,
            content_type=mime_type,
            storage_key=storage_key,
            old_stored_file=old_stored_file,
            attach=lambda stored_file: self.kp_repository.upsert_requirement_file_link(
                booking_service_id=booking_service.id,
                requirement_id=requirement.id,
                stored_file_id=stored_file.id,
            ),
        )
        return requirement_file

    async def get_booking_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> KpEventBookingServiceFileLink | None:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        await self._get_requirement_for_booking_service(booking_service, requirement_id)
        requirement_file = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement_id
        )
        if requirement_file is None or requirement_file.stored_file is None:
            return None
        return requirement_file

    async def get_booking_requirement_text(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> RequirementTextResponse | None:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        requirement = await self._get_requirement_for_booking_service(
            booking_service, requirement_id
        )
        if requirement.type != KpEventServiceRequirementType.TEXT:
            raise KpRequirementTextAnswerNotAllowed(
                f"booking_requirement:not_text:{requirement.id}"
            )
        requirement_answer = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement.id
        )
        if requirement_answer is None or requirement_answer.text_value is None:
            return None
        return RequirementTextResponse(
            id=requirement_answer.id,
            booking_service_id=requirement_answer.booking_service_id,
            requirement_id=requirement_answer.requirement_id,
            text_value=requirement_answer.text_value,
        )

    async def upsert_booking_requirement_text(
        self, booking_service_id: UUID, requirement_id: UUID, text_value: str
    ) -> RequirementTextResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        self._ensure_booking_editable_by_company(
            booking_service.booking, "upsert_booking_requirement_text"
        )
        requirement = await self._get_requirement_for_booking_service(
            booking_service, requirement_id
        )
        if requirement.type != KpEventServiceRequirementType.TEXT:
            raise KpRequirementTextAnswerNotAllowed(
                f"booking_requirement:not_text:{requirement.id}"
            )

        answer = text_value.strip()
        old_answer = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement.id
        )
        old_stored_file = old_answer.stored_file if old_answer is not None else None
        requirement_answer = await self.kp_repository.upsert_requirement_text_answer(
            booking_service_id=booking_service.id,
            requirement_id=requirement.id,
            text_value=answer,
        )
        if old_stored_file is not None:
            await self.storage_service.delete_object(old_stored_file.storage_key)
            await self.kp_repository.delete_stored_file(old_stored_file)
        return RequirementTextResponse(
            id=requirement_answer.id,
            booking_service_id=requirement_answer.booking_service_id,
            requirement_id=requirement_answer.requirement_id,
            text_value=requirement_answer.text_value or "",
        )

    async def delete_booking_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> None:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        self._ensure_booking_editable_by_company(
            booking_service.booking, "delete_booking_requirement_file"
        )
        await self._get_requirement_for_booking_service(booking_service, requirement_id)
        requirement_file = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement_id
        )
        if requirement_file is None or requirement_file.stored_file is None:
            return
        await delete_attached_file(
            storage_service=self.storage_service,
            kp_repository=self.kp_repository,
            old_stored_file=requirement_file.stored_file,
            detach=lambda: self.kp_repository.delete_requirement_file_link(
                requirement_file
            ),
        )

    async def get_booking_requirement_file_download_url(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> str:
        requirement_file = await self.get_booking_requirement_file(
            booking_service_id, requirement_id
        )
        if requirement_file is None or requirement_file.stored_file is None:
            raise KpServiceRequirementNotFound(
                f"booking_requirement_file:not_found:{booking_service_id}:{requirement_id}"
            )
        return await self.storage_service.generate_download_url(
            requirement_file.stored_file.storage_key,
            requirement_file.stored_file.original_filename,
        )

    async def get_staff_booking_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> KpEventBookingServiceFileLink | None:
        require_staff_user(self.current_user)
        booking_service = await self._get_booking_service(booking_service_id)
        await self._get_requirement_for_booking_service(booking_service, requirement_id)
        requirement_file = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement_id
        )
        if requirement_file is None or requirement_file.stored_file is None:
            return None
        return requirement_file

    async def get_staff_booking_requirement_file_download_url(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> str:
        requirement_file = await self.get_staff_booking_requirement_file(
            booking_service_id, requirement_id
        )
        if requirement_file is None or requirement_file.stored_file is None:
            raise KpServiceRequirementNotFound(
                f"staff_booking_requirement_file:not_found:{booking_service_id}:{requirement_id}"
            )
        return await self.storage_service.generate_download_url(
            requirement_file.stored_file.storage_key,
            requirement_file.stored_file.original_filename,
        )

    async def list_staff_booking_requirement_files(
        self, event_id: UUID, booking_id: UUID
    ) -> BookingRequirementFileMapResponse:
        require_staff_user(self.current_user)
        await self._get_event(event_id)
        booking = await self._get_booking(booking_id)
        if booking.event_id != event_id:
            raise KpBookingNotFound(
                f"staff_booking_requirement_files:event_mismatch:{event_id}:{booking_id}"
            )

        files: dict[UUID, RequirementFileResponse] = {}
        for booking_service in booking.services:
            for requirement_file in booking_service.requirement_file_links:
                if requirement_file.stored_file is None:
                    continue
                files[requirement_file.requirement_id] = RequirementFileResponse(
                    id=requirement_file.id,
                    booking_service_id=requirement_file.booking_service_id,
                    requirement_id=requirement_file.requirement_id,
                    stored_file=StoredFileResponse.model_validate(
                        requirement_file.stored_file, from_attributes=True
                    ),
                )
        return BookingRequirementFileMapResponse(files=files)

    async def cleanup_orphaned_stored_files(self) -> None:
        orphaned_files = await self.kp_repository.list_orphaned_stored_files(
            self.settings.STORAGE_ORPHAN_CLEANUP_MAX_AGE_HOURS
        )
        for stored_file in orphaned_files:
            await self.storage_service.delete_object(stored_file.storage_key)
            await self.kp_repository.delete_stored_file(stored_file)

    async def create_kp(self, create_kp_input: CreateKpInput) -> KpEvent:
        require_kp_president_user(self.current_user)
        existing = await self.kp_repository.get_by_name(create_kp_input.name)
        if existing is not None:
            raise KpNameExists(f"create_kp:{create_kp_input.name}")

        return await self.kp_repository.create_kp(create_kp_input)
