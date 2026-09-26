from collections.abc import Sequence
from datetime import date, datetime, timezone
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
    CompanyProfileIncomplete,
    CompanyProfileUnconfirmed,
    KpBookingAlreadyExists,
    KpBookingDeleteRequiresForce,
    KpBookingNotFound,
    KpBookingNotOwned,
    KpBookingReadonly,
    KpBookingStatusTransitionInvalid,
    KpBookingZoneLocked,
    KpBookingZoneSwitchNotAllowed,
    KpBoothNumberTaken,
    KpBoothZoneAtCapacity,
    KpBoothZoneColorExists,
    KpBoothZoneEventMismatch,
    KpBoothZoneFull,
    KpBoothZoneInUse,
    KpBoothZoneNameExists,
    KpBoothZoneNotFound,
    KpEventNotFound,
    KpFinalizationDeadlinePassed,
    KpIncludedExceedsMax,
    KpIncludedServiceDuplicate,
    KpNameExists,
    KpNametagLimitReached,
    KpNametagsDeadlinePassed,
    KpRegistrationClosed,
    KpRequirementBookingServiceMismatch,
    KpRequirementFileUploadNotAllowed,
    KpRequirementTextAnswerNotAllowed,
    KpServiceEventMismatch,
    KpServiceInUse,
    KpServiceNameExists,
    KpServiceNotFound,
    KpServiceQuantityInvalid,
    KpServiceRequirementNotFound,
    KpServiceUnavailable,
    KpWaitlistSameZone,
    KpWaitlistZoneHasCapacity,
)
from app.models.company import BOOKING_REQUIRED_PROFILE_FIELDS, KpCompanyProfile
from app.models.kp_event import (
    UNLIMITED_TOTAL_QUANTITY,
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
    KpServiceCategory,
    NameTag,
)
from app.models.user import User
from app.repositories.kp_repository import KpRepository
from app.schemas.kp import (
    BookingAdditionalServiceChargeResponse,
    BookingRequirementFileMapResponse,
    BookingResponse,
    BookingServiceInput,
    BookingServiceResponse,
    BookingUpgradeWaitlistEntryResult,
    BookingWithCompanyAndBoothZoneResponse,
    BoothZoneResponse,
    BoothZoneWithAvailabilityResult,
    CloneKpInput,
    CreateBookingInput,
    CreateBoothZoneInput,
    CreateKpInput,
    CreateServiceInput,
    IncludedServiceInput,
    MyBookingResponse,
    NameTagInput,
    NameTagResult,
    RejectBookingInput,
    RequirementFileResponse,
    RequirementTextResponse,
    ServiceRequirementResponse,
    ServiceResponse,
    StaffBookingServiceInput,
    StaffBookingUpgradeWaitlistEntryResult,
    StaffBoothZoneResponse,
    StaffUpdateBookingInput,
    StoredFileResponse,
    UpdateBookingBoothNumberInput,
    UpdateBookingInput,
    UpdateBookingStatusInput,
    UpdateBoothZoneInput,
    UpdateKpInput,
    UpdateServiceInput,
)
from app.schemas.pricing import PriceBreakdown
from app.services.booking_completeness import booking_completeness
from app.services.booking_notifier import (
    BookingNotifier,
    SilentBookingNotifier,
    notify_best_effort,
)
from app.services.booth_zone_view import (
    booth_zone_response,
    booth_zones_with_availability,
    staff_booth_zone_response,
)
from app.services.download_urls import DownloadUrls
from app.services.pricing import price_breakdown
from app.services.storage_service import StorageService, UploadKind, UploadStream
from app.services.waitlist_promotion import promote_waitlist
from app.services.zone_switch_stock import service_exceeding_stock

LAYOUT_FILE_CONTEXT = "booth_zone_layout"

REQUIREMENT_UPLOAD_KINDS = {
    KpEventServiceRequirementType.IMAGE: UploadKind.IMAGE,
    KpEventServiceRequirementType.PDF: UploadKind.PDF,
    KpEventServiceRequirementType.VIDEO: UploadKind.VIDEO,
}

BookingTransitions = dict[KpBookingStatus, frozenset[KpBookingStatus]]

COMPANY_BOOKING_TRANSITIONS: BookingTransitions = {
    KpBookingStatus.REGISTERED: frozenset({KpBookingStatus.CANCELLED}),
    KpBookingStatus.CONFIRMED: frozenset(),
    KpBookingStatus.CANCELLED: frozenset(),
    KpBookingStatus.REJECTED: frozenset(),
}

STAFF_BOOKING_TRANSITIONS: BookingTransitions = {
    KpBookingStatus.REGISTERED: frozenset(
        {KpBookingStatus.CONFIRMED, KpBookingStatus.REJECTED}
    ),
    KpBookingStatus.CONFIRMED: frozenset({KpBookingStatus.REGISTERED}),
    KpBookingStatus.CANCELLED: frozenset(),
    KpBookingStatus.REJECTED: frozenset(),
}


def waitlist_position(
    queue: Sequence[KpEventBookingUpgradeWaitlist], entry_id: UUID
) -> int:
    position = 1
    for other in queue:
        if other.id == entry_id:
            break
        if other.booking.status == KpBookingStatus.REGISTERED:
            position += 1
    return position


def ensure_booking_transition(
    transitions: BookingTransitions,
    booking: KpEventBooking,
    next_status: KpBookingStatus,
    context: str,
) -> None:
    if next_status not in transitions.get(booking.status, frozenset()):
        raise KpBookingStatusTransitionInvalid(
            f"{context}:{booking.id}:{booking.status}->{next_status}"
        )


class KpService:
    def __init__(
        self,
        kp_repository: KpRepository,
        storage_service: StorageService,
        current_user: User,
        notifier: BookingNotifier | None = None,
    ) -> None:
        self.kp_repository = kp_repository
        self.storage_service = storage_service
        self.download_urls = DownloadUrls(storage_service)
        self.current_user = current_user
        self.notifier = notifier or SilentBookingNotifier()
        self.settings = get_settings()

    async def _promote_waitlist(self, event_id: UUID, booth_zone_id: UUID) -> None:
        await promote_waitlist(
            self.kp_repository, self.notifier, event_id, booth_zone_id
        )

    async def _get_event(self, event_id: UUID) -> KpEvent:
        event = await self.kp_repository.get_by_id(event_id)
        if event is None:
            raise KpEventNotFound(f"event:not_found:{event_id}")
        return event

    async def list_kps(self) -> Sequence[KpEvent]:
        return await self.kp_repository.list_kps()

    async def get_latest_kp(self) -> Optional[KpEvent]:
        return await self.kp_repository.get_latest_kp()

    async def get_event_by_id(self, event_id: UUID) -> KpEvent:
        return await self._get_event(event_id)

    async def get_event_settings(self, event_id: UUID) -> KpEvent:
        require_kp_president_user(self.current_user)
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

    async def list_booth_zones(self, event_id: UUID) -> list[StaffBoothZoneResponse]:
        require_staff_user(self.current_user)
        await self._get_event(event_id)
        zones = await self.kp_repository.list_booth_zones(event_id)
        return [await self._build_staff_booth_zone_response(zone) for zone in zones]

    async def _build_booth_zone_response(
        self, zone: KpEventBoothZone
    ) -> BoothZoneResponse:
        return await booth_zone_response(zone, self.download_urls)

    async def _build_staff_booth_zone_response(
        self, zone: KpEventBoothZone
    ) -> StaffBoothZoneResponse:
        return await staff_booth_zone_response(zone, self.download_urls)

    async def _get_booth_zone(self, booth_zone_id: UUID) -> KpEventBoothZone:
        zone = await self.kp_repository.get_booth_zone_by_id(booth_zone_id)
        if zone is None:
            raise KpBoothZoneNotFound(f"booth_zone:not_found:{booth_zone_id}")
        return zone

    async def _ensure_included_services_fit(
        self,
        event_id: UUID,
        context: str,
        included_services: Sequence[IncludedServiceInput],
    ) -> None:
        seen: set[UUID] = set()
        for included_service in included_services:
            service_id = included_service.service_id
            if service_id in seen:
                raise KpIncludedServiceDuplicate(f"{context}:duplicate:{service_id}")
            seen.add(service_id)
            service = await self.kp_repository.get_service_by_id(service_id)
            if service is None:
                raise KpServiceNotFound(f"{context}:service_not_found:{service_id}")
            if service.event_id != event_id:
                raise KpServiceEventMismatch(
                    f"{context}:service_event_mismatch:{service_id}"
                )
            if included_service.included_quantity > service.max_quantity_per_booking:
                raise KpIncludedExceedsMax(
                    f"{context}:included_exceeds_max:{service_id}:"
                    f"{included_service.included_quantity}"
                )

    async def _ensure_booth_zone_identity_free(
        self,
        event_id: UUID,
        context: str,
        name: str | None,
        color: str | None,
        current_id: UUID | None = None,
    ) -> None:
        if name is not None:
            by_name = await self.kp_repository.get_booth_zone_by_name(event_id, name)
            if by_name is not None and by_name.id != current_id:
                raise KpBoothZoneNameExists(f"{context}:name:{event_id}:{name}")
        if color is not None:
            by_color = await self.kp_repository.get_booth_zone_by_color(event_id, color)
            if by_color is not None and by_color.id != current_id:
                raise KpBoothZoneColorExists(f"{context}:color:{event_id}:{color}")

    async def create_booth_zone(
        self, event_id: UUID, create_booth_zone_input: CreateBoothZoneInput
    ) -> StaffBoothZoneResponse:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        await self._ensure_booth_zone_identity_free(
            event_id,
            "create_booth_zone",
            create_booth_zone_input.name,
            create_booth_zone_input.color,
        )
        await self._ensure_included_services_fit(
            event_id, "create_booth_zone", create_booth_zone_input.included_services
        )
        zone = await self.kp_repository.create_booth_zone(
            event_id, create_booth_zone_input
        )
        return await self._build_staff_booth_zone_response(zone)

    async def update_booth_zone(
        self, booth_zone_id: UUID, update_booth_zone_input: UpdateBoothZoneInput
    ) -> StaffBoothZoneResponse:
        require_kp_president_user(self.current_user)
        zone = await self._get_booth_zone(booth_zone_id)
        updates = update_booth_zone_input.model_dump(exclude_unset=True)
        new_name = updates.get("name")
        new_color = updates.get("color")
        await self._ensure_booth_zone_identity_free(
            zone.event_id,
            "update_booth_zone",
            new_name if new_name != zone.name else None,
            new_color if new_color != zone.color else None,
            zone.id,
        )
        if update_booth_zone_input.included_services is not None:
            await self._ensure_included_services_fit(
                zone.event_id,
                "update_booth_zone",
                update_booth_zone_input.included_services,
            )
        previous_capacity = zone.capacity
        updated = await self.kp_repository.update_booth_zone(
            zone, update_booth_zone_input
        )
        if updated.capacity > previous_capacity:
            await self._promote_waitlist(updated.event_id, updated.id)
        return await self._build_staff_booth_zone_response(updated)

    async def delete_booth_zone(self, booth_zone_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        zone = await self._get_booth_zone(booth_zone_id)
        active_bookings = await self.kp_repository.count_active_bookings_for_zone(
            zone.event_id, zone.id
        )
        if active_bookings > 0:
            raise KpBoothZoneInUse(
                f"delete_booth_zone:in_use:{booth_zone_id}:{active_bookings}"
            )
        stored_file = zone.layout_stored_file
        await self.kp_repository.delete_booth_zone(zone)
        if stored_file is not None:
            await self.storage_service.delete_object(stored_file.storage_key)
            await self.kp_repository.delete_stored_file(stored_file)

    async def upload_booth_zone_layout_file(
        self,
        booth_zone_id: UUID,
        filename: str,
        upload: UploadStream,
        content_length: int | None,
        content_type: str | None,
    ) -> StaffBoothZoneResponse:
        require_kp_president_user(self.current_user)
        zone = await self._get_booth_zone(booth_zone_id)
        error_context = f"{LAYOUT_FILE_CONTEXT}:{booth_zone_id}"
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=UploadKind.PDF,
            error_context=error_context,
        )
        mime_type = self.storage_service.validate_image_or_pdf_file(
            filename,
            content,
            content_type,
            error_context=error_context,
        )
        old_stored_file = zone.layout_stored_file
        storage_key = (
            f"kp/booth-zones/{booth_zone_id}/layout/{uuid4()}{Path(filename).suffix}"
        )
        stored_object = await self.storage_service.upload_bytes(
            key=storage_key,
            content=content,
            filename=filename,
            content_type=mime_type,
        )
        try:
            stored_file = await self.kp_repository.upsert_stored_file(
                storage_key=stored_object.key,
                original_filename=filename,
                mime_type=stored_object.mime_type,
                size_bytes=stored_object.size_bytes,
                sha256=stored_object.sha256,
                etag=stored_object.etag,
                stored_file=None,
            )
            updated = await self.kp_repository.set_booth_zone_layout_stored_file_id(
                zone, stored_file.id
            )
        except Exception:
            await self.storage_service.delete_object(stored_object.key)
            raise
        if old_stored_file is not None:
            await self.storage_service.delete_object(old_stored_file.storage_key)
            await self.kp_repository.delete_stored_file(old_stored_file)
        return await self._build_staff_booth_zone_response(updated)

    async def delete_booth_zone_layout_file(
        self, booth_zone_id: UUID
    ) -> StaffBoothZoneResponse:
        require_kp_president_user(self.current_user)
        zone = await self._get_booth_zone(booth_zone_id)
        stored_file = zone.layout_stored_file
        if stored_file is None:
            return await self._build_staff_booth_zone_response(zone)
        updated = await self.kp_repository.set_booth_zone_layout_stored_file_id(
            zone, None
        )
        await self.storage_service.delete_object(stored_file.storage_key)
        await self.kp_repository.delete_stored_file(stored_file)
        return await self._build_staff_booth_zone_response(updated)

    async def _service_image_url(self, service: KpEventService) -> str | None:
        return await self.download_urls.of(service.image_stored_file)

    async def _remaining_total_quantity(self, service: KpEventService) -> int | None:
        if service.max_total_quantity == UNLIMITED_TOTAL_QUANTITY:
            return None
        charged = await self.kp_repository.count_active_charged_service_quantity(
            service.id
        )
        return max(service.max_total_quantity - charged, 0)

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
            image_url=await self._service_image_url(service),
            confirmation_description=service.confirmation_description,
            order=service.order,
            price=service.price,
            max_quantity_per_booking=service.max_quantity_per_booking,
            max_total_quantity=service.max_total_quantity,
            remaining_total_quantity=remaining_total_quantity,
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
        self, event_id: UUID, category: KpServiceCategory | None = None
    ) -> list[ServiceResponse]:
        require_confirmed_company_user(self.current_user)
        await self._get_event(event_id)
        services = await self.kp_repository.list_services(event_id, category)
        return [
            await self._build_service_response(
                service, await self._remaining_total_quantity(service)
            )
            for service in services
            if service.is_active
        ]

    async def _ensure_service_name_free(
        self,
        event_id: UUID,
        context: str,
        name: str | None,
        current_id: UUID | None = None,
    ) -> None:
        if name is None:
            return
        existing = await self.kp_repository.get_service_by_name(event_id, name)
        if existing is not None and existing.id != current_id:
            raise KpServiceNameExists(f"{context}:{event_id}:{name}")

    async def create_service(
        self, event_id: UUID, create_service_input: CreateServiceInput
    ) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        await self._ensure_service_name_free(
            event_id, "create_service", create_service_input.name
        )
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
        new_name = update_service_input.model_dump(exclude_unset=True).get("name")
        await self._ensure_service_name_free(
            service.event_id,
            "update_service",
            new_name if new_name != service.name else None,
            service.id,
        )
        await self._ensure_max_quantity_covers_inclusions(
            service, update_service_input.max_quantity_per_booking
        )
        updated = await self.kp_repository.update_service(service, update_service_input)
        return await self._build_service_response(updated)

    async def _ensure_max_quantity_covers_inclusions(
        self, service: KpEventService, max_quantity_per_booking: int | None
    ) -> None:
        if max_quantity_per_booking is None:
            return
        included_quantity = await self.kp_repository.max_included_quantity(service.id)
        if included_quantity > max_quantity_per_booking:
            raise KpIncludedExceedsMax(
                f"update_service:included_exceeds_max:{service.id}:{included_quantity}"
            )

    async def delete_service(self, service_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        active_bookings = await self.kp_repository.count_active_bookings_with_service(
            service_id
        )
        if active_bookings > 0:
            raise KpServiceInUse(
                f"delete_service:in_use:{service_id}:{active_bookings}"
            )
        await self.kp_repository.delete_service(service)

    async def upload_service_image(
        self,
        service_id: UUID,
        filename: str,
        upload: UploadStream,
        content_length: int | None,
        content_type: str | None,
    ) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        error_context = f"service_image:{service_id}"
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=UploadKind.IMAGE,
            error_context=error_context,
        )
        mime_type = self.storage_service.validate_image_file(
            filename,
            content,
            content_type,
            error_context=error_context,
        )
        old_stored_file = service.image_stored_file
        old_storage_key = (
            old_stored_file.storage_key if old_stored_file is not None else None
        )
        suffix = Path(filename).suffix
        storage_key = f"kp/services/{service_id}/image/{uuid4()}{suffix}"
        stored_object = await self.storage_service.upload_bytes(
            key=storage_key,
            content=content,
            filename=filename,
            content_type=mime_type,
        )
        try:
            stored_file = await self.kp_repository.upsert_stored_file(
                storage_key=stored_object.key,
                original_filename=filename,
                mime_type=stored_object.mime_type,
                size_bytes=stored_object.size_bytes,
                sha256=stored_object.sha256,
                etag=stored_object.etag,
                stored_file=None,
            )
            updated = await self.kp_repository.set_service_image_stored_file_id(
                service, stored_file.id
            )
        except Exception:
            await self.storage_service.delete_object(stored_object.key)
            raise
        if old_storage_key is not None and old_storage_key != stored_object.key:
            await self.storage_service.delete_object(old_storage_key)
        if old_stored_file is not None:
            await self.kp_repository.delete_stored_file(old_stored_file)
        return await self._build_service_response(updated)

    async def delete_service_image(self, service_id: UUID) -> ServiceResponse:
        require_kp_president_user(self.current_user)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        stored_file = service.image_stored_file
        if stored_file is None:
            return await self._build_service_response(service)
        storage_key = stored_file.storage_key
        updated = await self.kp_repository.set_service_image_stored_file_id(
            service, None
        )
        await self.storage_service.delete_object(storage_key)
        await self.kp_repository.delete_stored_file(stored_file)
        return await self._build_service_response(updated)

    async def _is_registration_open(self, event: KpEvent, company_id: UUID) -> bool:
        if event.is_registration_open():
            return True
        exception = await self.kp_repository.get_registration_exception(
            event.id, company_id
        )
        return exception is not None and exception.allowed_until >= date.today()

    async def _ensure_registration_open(self, event: KpEvent, company_id: UUID) -> None:
        if not await self._is_registration_open(event, company_id):
            raise KpRegistrationClosed(
                f"register_booking:closed:{event.id}:{company_id}"
            )

    async def list_booth_zones_for_company(
        self, event_id: UUID
    ) -> list[BoothZoneWithAvailabilityResult]:
        require_confirmed_company_user(self.current_user)
        await self._get_event(event_id)
        return await booth_zones_with_availability(
            self.kp_repository, self.download_urls, event_id
        )

    async def _validate_service_quantity(
        self,
        *,
        event_id: UUID,
        service_id: UUID,
        stored_quantity: int,
        existing_quantity: int,
        included_quantity: int,
        context: str,
    ) -> None:
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"{context}:service_not_found:{service_id}")
        if service.event_id != event_id or not service.is_active:
            raise KpServiceUnavailable(f"{context}:service_unavailable:{service_id}")
        if stored_quantity > service.max_quantity_per_booking:
            raise KpServiceQuantityInvalid(
                f"booking_service:service_max_per_booking:{service_id}:{stored_quantity}"
            )
        charged_quantity = max(stored_quantity - included_quantity, 0) - max(
            existing_quantity - included_quantity, 0
        )
        if (
            service.max_total_quantity != UNLIMITED_TOTAL_QUANTITY
            and charged_quantity > 0
        ):
            booked_quantity = (
                await self.kp_repository.count_active_charged_service_quantity(
                    service_id
                )
            )
            if booked_quantity + charged_quantity > service.max_total_quantity:
                raise KpServiceQuantityInvalid(
                    f"{context}:service_max_total:{service_id}:{charged_quantity}"
                )

    async def _validate_booking_services(
        self,
        event_id: UUID,
        services: Sequence[BookingServiceInput],
        existing_quantities: dict[UUID, int] | None = None,
        included_quantities: dict[UUID, int] | None = None,
    ) -> list[BookingServiceInput]:
        existing_quantities = existing_quantities or {}
        included_quantities = included_quantities or {}
        service_quantities: dict[UUID, int] = {}
        for booking_service in services:
            service_quantities[booking_service.service_id] = (
                service_quantities.get(booking_service.service_id, 0)
                + booking_service.quantity
            )

        validated_services: list[BookingServiceInput] = []
        for service_id, quantity in service_quantities.items():
            existing_quantity = existing_quantities.get(service_id, 0)
            included_quantity = included_quantities.get(service_id, 0)
            await self._validate_service_quantity(
                event_id=event_id,
                service_id=service_id,
                stored_quantity=max(existing_quantity + quantity, included_quantity),
                existing_quantity=existing_quantity,
                included_quantity=included_quantity,
                context="register_booking",
            )
            validated_services.append(
                BookingServiceInput(service_id=service_id, quantity=quantity)
            )
        return validated_services

    async def _lock_zone_until_booking_is_inserted(
        self, booth_zone_id: UUID, context: str = "register_booking"
    ) -> KpEventBoothZone:
        locked_zone = await self.kp_repository.lock_model_by_id(
            KpEventBoothZone, booth_zone_id
        )
        if locked_zone is None:
            raise KpBoothZoneNotFound(
                f"{context}:locked_zone_not_found:{booth_zone_id}"
            )
        return locked_zone

    def _ensure_finalization_deadline_open(
        self, booking: KpEventBooking, context: str
    ) -> None:
        if booking.event.is_finalization_deadline_passed():
            raise KpFinalizationDeadlinePassed(
                f"{context}:deadline_passed:{booking.id}:"
                f"{booking.event.finalization_deadline}"
            )

    def _ensure_booking_editable_by_company(
        self, booking: KpEventBooking, context: str
    ) -> None:
        if not booking.is_active:
            raise KpBookingReadonly(f"{context}:readonly:{booking.id}:{booking.status}")
        self._ensure_finalization_deadline_open(booking, context)

    def _ensure_zone_unlocked(self, booking: KpEventBooking, context: str) -> None:
        if booking.status == KpBookingStatus.CONFIRMED:
            raise KpBookingZoneLocked(f"{context}:zone_locked:{booking.id}")

    async def _build_booking_response(self, booking: KpEventBooking) -> BookingResponse:
        services, additional_service_charges = await self._build_booking_services(
            booking
        )
        booth_zone_model = getattr(booking, "booth_zone", None)
        booth_zone = (
            await self._build_booth_zone_response(booth_zone_model)
            if booth_zone_model is not None
            else None
        )
        net_total = self._booking_net_total(booking)
        missing_items = booking_completeness(booking)
        return BookingResponse(
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
            missing_items=missing_items,
            is_complete=not missing_items,
            booth_zone=booth_zone,
            services=services,
            additional_service_charges=additional_service_charges,
            net_total=net_total,
            price=self._booking_price(booking, net_total),
        )

    def _booking_net_total(self, booking: KpEventBooking) -> int:
        booth_zone = getattr(booking, "booth_zone", None)
        base_price = booth_zone.base_price if booth_zone is not None else 0
        return base_price + sum(
            self._service_line_net(booking_service)
            for booking_service in booking.services
        )

    def _service_line_net(self, booking_service: KpEventBookingService) -> int:
        return booking_service.charged_quantity * booking_service.service.price

    def _booking_price(self, booking: KpEventBooking, net_total: int) -> PriceBreakdown:
        return price_breakdown(net_total, booking.event.vat_rate_permille)

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
                charged_quantity=booking_service.charged_quantity,
                unit_price=booking_service.service.price,
                line_net=self._service_line_net(booking_service),
                service=await self._build_service_response(booking_service.service),
            )
            for booking_service in booking.services
        ]
        additional_service_charges = [
            BookingAdditionalServiceChargeResponse(
                name=booking_service.service.name,
                quantity=booking_service.quantity,
                charged_quantity=booking_service.charged_quantity,
                line_net=self._service_line_net(booking_service),
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
        booth_zone = await self._build_staff_booth_zone_response(booking.booth_zone)
        net_total = self._booking_net_total(booking)
        missing_items = booking_completeness(booking)
        return BookingWithCompanyAndBoothZoneResponse(
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
            missing_items=missing_items,
            is_complete=not missing_items,
            company=booking.company,
            booth_zone=booth_zone,
            services=services,
            additional_service_charges=additional_service_charges,
            net_total=net_total,
            price=self._booking_price(booking, net_total),
            booked_services_count=booking.booked_services_count,
            booked_services_summary=booking.booked_services_summary,
            nametag_count=booking.nametag_count,
            waitlist_count=booking.waitlist_count,
            company_details_submitted=booking.company_details_submitted,
            status_note=booking.status_note,
        )

    async def _confirmed_company_profile(
        self, company_id: UUID, confirm_profile: bool
    ) -> KpCompanyProfile:
        if not confirm_profile:
            raise CompanyProfileUnconfirmed(
                f"register_booking:profile_unconfirmed:{company_id}"
            )
        profile = await self.kp_repository.get_company_profile(company_id)
        missing = (
            profile.missing_booking_profile_fields()
            if profile is not None
            else list(BOOKING_REQUIRED_PROFILE_FIELDS)
        )
        if profile is None or missing:
            raise CompanyProfileIncomplete(
                f"register_booking:profile_incomplete:{company_id}", missing
            )
        return profile

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
        company_profile = await self._confirmed_company_profile(
            company_user.company_id, confirm_profile
        )

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

        locked_zone = await self._lock_zone_until_booking_is_inserted(booth_zone_id)

        count = await self.kp_repository.count_active_bookings_for_zone(
            event_id, booth_zone_id
        )
        if count >= locked_zone.capacity:
            raise KpBoothZoneAtCapacity(f"register_booking:at_capacity:{booth_zone_id}")

        validated_services = await self._validate_booking_services(
            event_id,
            services,
            included_quantities={
                included_service.service_id: included_service.included_quantity
                for included_service in locked_zone.included_services
            },
        )
        booking = await self.kp_repository.create_booking(
            event_id=event_id,
            company_id=company_user.company_id,
            booth_zone_id=booth_zone_id,
            create_booking_input=CreateBookingInput(status=KpBookingStatus.REGISTERED),
            services=validated_services,
            included_services=locked_zone.included_services,
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

        locked_event = await self.kp_repository.lock_model_by_id(
            KpEvent, booking.event_id
        )
        if locked_event is None:
            raise KpEventNotFound(
                f"add_booking_services:locked_event_not_found:{booking.event_id}"
            )

        validated_services = await self._validate_booking_services(
            booking.event_id,
            services,
            existing_quantities={
                booking_service.service_id: booking_service.quantity
                for booking_service in booking.services
            },
            included_quantities={
                booking_service.service_id: booking_service.included_quantity
                for booking_service in booking.services
            },
        )
        updated = await self.kp_repository.add_booking_services(
            booking,
            validated_services,
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

    async def list_bookings_for_event(
        self, event_id: UUID
    ) -> list[BookingWithCompanyAndBoothZoneResponse]:
        require_staff_user(self.current_user)
        await self._get_event(event_id)
        bookings = await self.kp_repository.list_bookings_for_event(event_id)
        return [
            await self._build_staff_booking_response(booking) for booking in bookings
        ]

    async def get_event_booking(
        self, event_id: UUID, booking_id: UUID
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        await self._get_event(event_id)
        booking = await self._get_booking(booking_id)
        if booking.event_id != event_id:
            raise KpBookingNotFound(f"booking:event_mismatch:{event_id}:{booking_id}")
        return await self._build_staff_booking_response(booking)

    async def _get_owned_booking(
        self, booking_id: UUID, company_id: UUID, context: str
    ) -> KpEventBooking:
        booking = await self.kp_repository.get_booking_by_id(booking_id)
        if booking is None:
            raise KpBookingNotFound(f"{context}:not_found:{booking_id}")
        if booking.company_id != company_id:
            raise KpBookingNotOwned(f"{context}:not_owned:{booking_id}")
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

    async def _free_spots_in_zone(self, zone: KpEventBoothZone) -> int:
        taken = await self.kp_repository.count_active_bookings_for_zone(
            zone.event_id, zone.id
        )
        return max(zone.capacity - taken, 0)

    def _ensure_nametags_editable(self, booking: KpEventBooking, context: str) -> None:
        if not booking.is_active:
            raise KpBookingReadonly(f"{context}:readonly:{booking.id}:{booking.status}")
        if booking.event.is_nametags_deadline_passed():
            raise KpNametagsDeadlinePassed(
                f"{context}:deadline_passed:{booking.id}:"
                f"{booking.event.nametags_deadline}"
            )

    def _name_tag_result(self, name_tag: NameTag) -> NameTagResult:
        return NameTagResult(
            id=name_tag.id,
            booking_id=name_tag.booking_id,
            first_name=name_tag.first_name,
            last_name=name_tag.last_name,
            position=name_tag.position,
        )

    async def _booking_name_tags(self, booking_id: UUID) -> list[NameTagResult]:
        name_tags = await self.kp_repository.list_name_tags_for_booking(booking_id)
        return [self._name_tag_result(name_tag) for name_tag in name_tags]

    async def list_booking_name_tags(self, booking_id: UUID) -> list[NameTagResult]:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "list_booking_name_tags"
        )
        return await self._booking_name_tags(booking.id)

    async def list_booking_name_tags_for_staff(
        self, booking_id: UUID
    ) -> list[NameTagResult]:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        return await self._booking_name_tags(booking.id)

    async def replace_booking_name_tags(
        self, booking_id: UUID, name_tags: Sequence[NameTagInput]
    ) -> list[NameTagResult]:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "replace_booking_name_tags"
        )
        self._ensure_nametags_editable(booking, "replace_booking_name_tags")
        maximum = booking.event.max_nametags_per_booking
        if len(name_tags) > maximum:
            raise KpNametagLimitReached(
                f"replace_booking_name_tags:limit_reached:{booking.id}:{maximum}"
            )
        replaced = await self.kp_repository.replace_name_tags(booking, name_tags)
        return [self._name_tag_result(name_tag) for name_tag in replaced]

    async def _build_staff_waitlist_entry(
        self, entry: KpEventBookingUpgradeWaitlist
    ) -> StaffBookingUpgradeWaitlistEntryResult:
        zone = entry.target_booth_zone
        queue = await self.kp_repository.list_waitlist_entries_for_zone(zone.id)
        free_spots = await self._free_spots_in_zone(zone)
        return StaffBookingUpgradeWaitlistEntryResult(
            id=entry.id,
            booking_id=entry.booking_id,
            target_booth_zone_id=entry.target_booth_zone_id,
            priority_rank=entry.priority_rank,
            target_booth_zone=await self._build_staff_booth_zone_response(zone),
            is_full=free_spots == 0,
            available_spots=free_spots,
            position=waitlist_position(queue, entry.id),
        )

    async def _build_waitlist_entry(
        self, entry: KpEventBookingUpgradeWaitlist
    ) -> BookingUpgradeWaitlistEntryResult:
        staff_entry = await self._build_staff_waitlist_entry(entry)
        return BookingUpgradeWaitlistEntryResult.model_validate(
            staff_entry.model_dump(
                exclude={"available_spots": True, "target_booth_zone": {"capacity"}}
            )
        )

    async def list_booking_upgrade_waitlist(
        self, booking_id: UUID
    ) -> list[BookingUpgradeWaitlistEntryResult]:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "list_booking_upgrade_waitlist"
        )
        entries = await self.kp_repository.list_booking_upgrade_waitlist_entries(
            booking.id
        )
        return [await self._build_waitlist_entry(entry) for entry in entries]

    async def list_booking_upgrade_waitlist_for_staff(
        self, booking_id: UUID
    ) -> list[StaffBookingUpgradeWaitlistEntryResult]:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        entries = await self.kp_repository.list_booking_upgrade_waitlist_entries(
            booking.id
        )
        return [await self._build_staff_waitlist_entry(entry) for entry in entries]

    async def replace_booking_upgrade_waitlist(
        self, booking_id: UUID, target_booth_zone_ids: list[UUID]
    ) -> list[BookingUpgradeWaitlistEntryResult]:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "replace_booking_upgrade_waitlist"
        )
        self._ensure_booking_editable_by_company(
            booking, "replace_booking_upgrade_waitlist"
        )
        self._ensure_zone_unlocked(booking, "replace_booking_upgrade_waitlist")

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
            if await self._free_spots_in_zone(target_zone) > 0:
                raise KpWaitlistZoneHasCapacity(
                    f"booking_upgrade_waitlist:has_capacity:{booking_id}:{target_zone.id}"
                )

        entries = await self.kp_repository.replace_booking_upgrade_waitlist_entries(
            booking=booking,
            target_booth_zone_ids=unique_target_ids,
        )
        return [await self._build_waitlist_entry(entry) for entry in entries]

    async def _ensure_zone_switch_stock(
        self, booking: KpEventBooking, zone: KpEventBoothZone, context: str
    ) -> None:
        service = await service_exceeding_stock(self.kp_repository, booking, zone)
        if service is not None:
            raise KpServiceQuantityInvalid(
                f"{context}:service_max_total:{service.id}:{zone.id}"
            )

    async def switch_booking_zone(
        self, booking_id: UUID, booth_zone_id: UUID
    ) -> BookingResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "switch_booking_zone"
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

        locked_event = await self.kp_repository.lock_model_by_id(
            KpEvent, booking.event_id
        )
        if locked_event is None:
            raise KpEventNotFound(
                f"switch_booking_zone:locked_event_not_found:{booking.event_id}"
            )

        zone = await self.kp_repository.get_booth_zone_by_id(booth_zone_id)
        if zone is None:
            raise KpBoothZoneNotFound(
                f"switch_booking_zone:zone_not_found:{booth_zone_id}"
            )
        if zone.event_id != booking.event_id:
            raise KpBoothZoneEventMismatch(
                f"switch_booking_zone:zone_event_mismatch:{booth_zone_id}"
            )

        locked_zone = await self._lock_zone_until_booking_is_inserted(
            booth_zone_id, "switch_booking_zone"
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

    async def update_my_booking_status(
        self, booking_id: UUID, update_booking_input: UpdateBookingStatusInput
    ) -> BookingResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(
            booking_id, company_user.company_id, "update_my_booking_status"
        )
        next_status = update_booking_input.status
        if booking.status == next_status:
            return await self._build_booking_response(booking)
        ensure_booking_transition(
            COMPANY_BOOKING_TRANSITIONS,
            booking,
            next_status,
            "update_my_booking_status",
        )
        updated = await self.kp_repository.update_booking(
            booking,
            UpdateBookingInput(
                status=next_status, status_changed_at=datetime.now(timezone.utc)
            ),
        )
        await self._promote_waitlist(updated.event_id, updated.booth_zone_id)
        return await self._build_booking_response(updated)

    async def update_booking_booth_number(
        self, booking_id: UUID, update_booking_input: UpdateBookingBoothNumberInput
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        booth_nr = update_booking_input.booth_nr
        await self._ensure_booth_number_free(
            booking, booking.booth_zone_id, booth_nr, "update_booking_booth_number"
        )
        updated = await self.kp_repository.update_booking(
            booking, UpdateBookingInput(booth_nr=booth_nr)
        )
        return await self._build_staff_booking_response(updated)

    async def accept_booking(
        self, booking_id: UUID
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        ensure_booking_transition(
            STAFF_BOOKING_TRANSITIONS,
            booking,
            KpBookingStatus.CONFIRMED,
            "accept_booking",
        )
        changed_at = datetime.now(timezone.utc)
        updated = await self.kp_repository.update_booking(
            booking,
            UpdateBookingInput(
                status=KpBookingStatus.CONFIRMED,
                status_changed_at=changed_at,
                confirmed_at=changed_at,
            ),
        )
        await notify_best_effort(self.notifier.booking_accepted(updated))
        return await self._build_staff_booking_response(updated)

    async def undo_accept_booking(
        self, booking_id: UUID
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        ensure_booking_transition(
            STAFF_BOOKING_TRANSITIONS,
            booking,
            KpBookingStatus.REGISTERED,
            "undo_accept_booking",
        )
        changed_at = datetime.now(timezone.utc)
        updated = await self.kp_repository.update_booking(
            booking,
            UpdateBookingInput(
                status=KpBookingStatus.REGISTERED,
                status_changed_at=changed_at,
                confirmed_at=None,
            ),
        )
        return await self._build_staff_booking_response(updated)

    async def reject_booking(
        self, booking_id: UUID, reject_booking_input: RejectBookingInput
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        ensure_booking_transition(
            STAFF_BOOKING_TRANSITIONS,
            booking,
            KpBookingStatus.REJECTED,
            "reject_booking",
        )
        changed_at = datetime.now(timezone.utc)
        updated = await self.kp_repository.update_booking(
            booking,
            UpdateBookingInput(
                status=KpBookingStatus.REJECTED,
                status_changed_at=changed_at,
                rejection_reason=reject_booking_input.reason,
            ),
        )
        await self._promote_waitlist(updated.event_id, updated.booth_zone_id)
        await notify_best_effort(
            self.notifier.booking_rejected(updated, reject_booking_input.reason)
        )
        return await self._build_staff_booking_response(updated)

    async def delete_booking(self, booking_id: UUID, force: bool = False) -> None:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        if booking.status == KpBookingStatus.CONFIRMED and not force:
            raise KpBookingDeleteRequiresForce(
                f"delete_booking:confirmed:{booking_id}:{booking.status}"
            )
        event_id = booking.event_id
        booth_zone_id = booking.booth_zone_id
        await self.kp_repository.delete_booking(booking)
        await self._promote_waitlist(event_id, booth_zone_id)

    async def _ensure_booth_number_free(
        self,
        booking: KpEventBooking,
        booth_zone_id: UUID,
        booth_nr: int | None,
        context: str,
    ) -> None:
        if booth_nr is None:
            return
        occupant = await self.kp_repository.get_active_booking_by_booth_number(
            booking.event_id, booth_zone_id, booth_nr
        )
        if occupant is not None and occupant.id != booking.id:
            raise KpBoothNumberTaken(f"{context}:taken:{booking.id}:{booth_nr}")

    async def _locked_target_booth_zone(
        self, booking: KpEventBooking, booth_zone_id: UUID
    ) -> KpEventBoothZone:
        zone = await self.kp_repository.get_booth_zone_by_id(booth_zone_id)
        if zone is None:
            raise KpBoothZoneNotFound(f"update_booking:zone_not_found:{booth_zone_id}")
        if zone.event_id != booking.event_id:
            raise KpBoothZoneEventMismatch(
                f"update_booking:zone_event_mismatch:{booth_zone_id}"
            )
        locked_zone = await self._lock_zone_until_booking_is_inserted(booth_zone_id)
        count = await self.kp_repository.count_active_bookings_for_zone(
            booking.event_id, booth_zone_id
        )
        if count >= locked_zone.capacity:
            raise KpBoothZoneAtCapacity(f"update_booking:at_capacity:{booth_zone_id}")
        return locked_zone

    async def _validated_service_quantities(
        self, booking: KpEventBooking, services: Sequence[StaffBookingServiceInput]
    ) -> dict[UUID, int]:
        existing_quantities = {
            booking_service.service_id: booking_service.quantity
            for booking_service in booking.services
        }
        included_quantities = {
            booking_service.service_id: booking_service.included_quantity
            for booking_service in booking.services
        }
        quantities: dict[UUID, int] = {}
        for item in services:
            included_quantity = included_quantities.get(item.service_id, 0)
            stored_quantity = max(item.quantity, included_quantity)
            await self._validate_service_quantity(
                event_id=booking.event_id,
                service_id=item.service_id,
                stored_quantity=stored_quantity,
                existing_quantity=existing_quantities.get(item.service_id, 0),
                included_quantity=included_quantity,
                context="update_booking",
            )
            quantities[item.service_id] = stored_quantity
        return quantities

    async def update_booking(
        self, booking_id: UUID, staff_update_booking_input: StaffUpdateBookingInput
    ) -> BookingWithCompanyAndBoothZoneResponse:
        require_staff_user(self.current_user)
        booking = await self._get_booking(booking_id)
        updates = staff_update_booking_input.model_dump(exclude_unset=True)

        updated = booking
        left_booth_zone_id: UUID | None = None
        target_zone_id = staff_update_booking_input.booth_zone_id
        if target_zone_id is not None and target_zone_id != booking.booth_zone_id:
            left_booth_zone_id = booking.booth_zone_id
            target_zone = await self._locked_target_booth_zone(booking, target_zone_id)
            await self._ensure_zone_switch_stock(booking, target_zone, "update_booking")
            updated = await self.kp_repository.move_booking_to_zone(
                booking, target_zone, clear_whole_waitlist=False
            )

        changes: dict[str, object] = {}
        if "booth_nr" in updates:
            await self._ensure_booth_number_free(
                updated,
                updated.booth_zone_id,
                staff_update_booking_input.booth_nr,
                "update_booking",
            )
            changes["booth_nr"] = staff_update_booking_input.booth_nr
        if "status_note" in updates:
            changes["status_note"] = staff_update_booking_input.status_note
        if changes:
            updated = await self.kp_repository.update_booking(
                updated, UpdateBookingInput.model_validate(changes)
            )
        if staff_update_booking_input.services is not None:
            quantities = await self._validated_service_quantities(
                updated, staff_update_booking_input.services
            )
            if quantities:
                updated = await self.kp_repository.set_booking_service_quantities(
                    updated, quantities
                )
        if left_booth_zone_id is not None:
            await self._promote_waitlist(updated.event_id, left_booth_zone_id)
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

    def _requirement_upload_kind(
        self, requirement: KpEventServiceRequirement
    ) -> UploadKind:
        if requirement.type == KpEventServiceRequirementType.TEXT:
            raise KpRequirementFileUploadNotAllowed(
                f"booking_requirement:not_file_upload:{requirement.id}"
            )
        return REQUIREMENT_UPLOAD_KINDS.get(requirement.type, UploadKind.FILE)

    def _validate_requirement_upload(
        self,
        kind: UploadKind,
        filename: str,
        content: bytes,
        content_type: str | None,
        *,
        error_context: str,
    ) -> str:
        if kind is UploadKind.IMAGE:
            return self.storage_service.validate_image_file(
                filename, content, content_type, error_context=error_context
            )

        if kind is UploadKind.PDF:
            return self.storage_service.validate_pdf_file(
                filename, content, content_type, error_context=error_context
            )

        if kind is UploadKind.VIDEO:
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
        upload: UploadStream,
        content_length: int | None = None,
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
        kind = self._requirement_upload_kind(requirement)
        error_context = f"booking_requirement:{requirement.type.value}:{requirement.id}"
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=kind,
            error_context=error_context,
        )
        mime_type = self._validate_requirement_upload(
            kind, filename, content, content_type, error_context=error_context
        )
        suffix = Path(filename).suffix
        storage_key = f"kp/booking-services/{booking_service.id}/requirements/{requirement.id}/{uuid4()}{suffix}"
        existing_file = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement.id
        )
        old_stored_file = (
            existing_file.stored_file if existing_file is not None else None
        )
        old_storage_key = old_stored_file.storage_key if old_stored_file else None
        stored_object = await self.storage_service.upload_bytes(
            key=storage_key,
            content=content,
            filename=filename,
            content_type=mime_type,
        )
        try:
            stored_file = await self.kp_repository.upsert_stored_file(
                storage_key=stored_object.key,
                original_filename=filename,
                mime_type=stored_object.mime_type,
                size_bytes=stored_object.size_bytes,
                sha256=stored_object.sha256,
                etag=stored_object.etag,
                stored_file=None,
            )
            requirement_file = await self.kp_repository.upsert_requirement_file_link(
                booking_service_id=booking_service.id,
                requirement_id=requirement.id,
                stored_file_id=stored_file.id,
            )
        except Exception:
            await self.storage_service.delete_object(stored_object.key)
            raise
        if old_storage_key is not None and old_storage_key != stored_object.key:
            await self.storage_service.delete_object(old_storage_key)
        if old_stored_file is not None:
            await self.kp_repository.delete_stored_file(old_stored_file)
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
        if requirement_file is None:
            return
        if requirement_file.stored_file is None:
            return
        await self.storage_service.delete_object(
            requirement_file.stored_file.storage_key
        )
        await self.kp_repository.delete_requirement_file_link(requirement_file)
        await self.kp_repository.delete_stored_file(requirement_file.stored_file)

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
