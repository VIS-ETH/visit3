from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from app.core.auth_context import (
    require_assigned_company_user,
    require_confirmed_company_user,
    require_kp_president_user,
)
from app.core.config import get_settings
from app.core.exceptions import (
    KpBookingAlreadyExists,
    KpBookingConfirmationRequiresFinalized,
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
    KpServiceNotFound,
    KpServiceRequirementNotFound,
    KpWaitlistSameZone,
)
from app.models.kp_event import (
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
    BoothZoneWithAvailabilityResult,
    CloneKpInput,
    CreateBookingInput,
    CreateBoothZoneInput,
    CreateIndustryInput,
    CreateKpInput,
    CreateServiceInput,
    UpdateBookingBoothNumberInput,
    UpdateBookingInput,
    UpdateBookingStatusInput,
    UpdateBoothZoneInput,
    UpdateKpInput,
    UpdateServiceInput,
)
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

    async def clone_kp(self, event_id: UUID, clone_kp_input: CloneKpInput) -> KpEvent:
        require_kp_president_user(
            self.current_user, self.settings.VISIT_KP_PRESIDENT_ROLE
        )
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

    async def list_services(self, event_id: UUID) -> Sequence[KpEventService]:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        return await self.kp_repository.list_services(event_id)

    async def create_service(
        self, event_id: UUID, create_service_input: CreateServiceInput
    ) -> KpEventService:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        return await self.kp_repository.create_service(event_id, create_service_input)

    async def update_service(
        self, service_id: UUID, update_service_input: UpdateServiceInput
    ) -> KpEventService:
        require_kp_president_user(self.current_user)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        return await self.kp_repository.update_service(service, update_service_input)

    async def delete_service(self, service_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        service = await self.kp_repository.get_service_by_id(service_id)
        if service is None:
            raise KpServiceNotFound(f"service:not_found:{service_id}")
        await self.kp_repository.delete_service(service)

    # --- Industries ---

    async def list_industries(self) -> Sequence[KpIndustry]:
        require_kp_president_user(self.current_user)
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

    async def register_booking(
        self, event_id: UUID, booth_zone_id: UUID
    ) -> KpEventBooking:
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

        return await self.kp_repository.create_booking(
            event_id=event_id,
            company_id=company_user.company_id,
            booth_zone_id=booth_zone_id,
            create_booking_input=CreateBookingInput(status=KpBookingStatus.REGISTERED),
        )

    async def get_my_booking(self, event_id: UUID) -> Optional[KpEventBooking]:
        company_user = require_assigned_company_user(self.current_user)
        await self._get_event(event_id)
        return await self.kp_repository.get_company_active_booking_for_event(
            event_id, company_user.company_id
        )

    # --- Bookings ---

    async def list_bookings_for_event(self, event_id: UUID) -> Sequence[KpEventBooking]:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        return await self.kp_repository.list_bookings_for_event(event_id)

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
        booking_service = await self.kp_repository.get_booking_service_by_id(
            booking_service_id
        )
        if booking_service is None:
            raise KpBookingNotFound(f"booking_service:not_found:{booking_service_id}")
        if booking_service.booking.company_id != company_id:
            raise KpBookingNotOwned(f"booking_service:not_owned:{booking_service_id}")
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

    async def update_my_booking_status(
        self, booking_id: UUID, update_booking_input: UpdateBookingStatusInput
    ) -> KpEventBooking:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self._get_owned_booking(booking_id, company_user.company_id)
        self._ensure_company_status_transition(booking, update_booking_input.status)
        return await self.kp_repository.update_booking(
            booking, UpdateBookingInput(status=update_booking_input.status)
        )

    async def update_booking_booth_number(
        self, booking_id: UUID, update_booking_input: UpdateBookingBoothNumberInput
    ) -> KpEventBooking:
        require_kp_president_user(self.current_user)
        booking = await self._get_booking(booking_id)
        return await self.kp_repository.update_booking(
            booking, UpdateBookingInput(booth_nr=update_booking_input.booth_nr)
        )

    async def confirm_booking(self, booking_id: UUID) -> KpEventBooking:
        require_kp_president_user(self.current_user)
        booking = await self._get_booking(booking_id)
        if booking.status != KpBookingStatus.FINALIZED:
            raise KpBookingConfirmationRequiresFinalized(
                f"booking_confirm:not_finalized:{booking_id}:{booking.status}"
            )
        return await self.kp_repository.update_booking(
            booking, UpdateBookingInput(status=KpBookingStatus.CONFIRMED)
        )

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
    ) -> None:
        if requirement.type == KpEventServiceRequirementType.TEXT:
            raise KpRequirementFileUploadNotAllowed(
                f"booking_requirement:not_file_upload:{requirement.id}"
            )

        error_context = f"booking_requirement:{requirement.type.value}:{requirement.id}"
        if requirement.type == KpEventServiceRequirementType.IMAGE:
            self.storage_service.validate_image_file(
                filename, content, content_type, error_context=error_context
            )
            return

        if requirement.type == KpEventServiceRequirementType.PDF:
            self.storage_service.validate_pdf_file(
                filename, content, content_type, error_context=error_context
            )
            return

        if requirement.type == KpEventServiceRequirementType.VIDEO:
            self.storage_service.validate_video_file(
                filename, content, content_type, error_context=error_context
            )
            return

        self.storage_service.validate_generic_file(
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
        requirement = await self._get_requirement_for_booking_service(
            booking_service, requirement_id
        )
        self._validate_requirement_upload(requirement, filename, content, content_type)
        suffix = Path(filename).suffix
        storage_key = f"kp/booking-services/{booking_service.id}/requirements/{requirement.id}/{uuid4()}{suffix}"
        existing_file = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement.id
        )
        old_storage_key = (
            existing_file.stored_file.storage_key if existing_file is not None else None
        )
        stored_object = await self.storage_service.upload_bytes(
            key=storage_key,
            content=content,
            filename=filename,
            content_type=content_type,
        )
        try:
            stored_file = await self.kp_repository.upsert_stored_file(
                storage_key=stored_object.key,
                original_filename=filename,
                mime_type=stored_object.mime_type,
                size_bytes=stored_object.size_bytes,
                sha256=stored_object.sha256,
                etag=stored_object.etag,
                stored_file=existing_file.stored_file
                if existing_file is not None
                else None,
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
        return requirement_file

    async def get_booking_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> KpEventBookingServiceFileLink | None:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        await self._get_requirement_for_booking_service(booking_service, requirement_id)
        return await self.kp_repository.get_requirement_file(
            booking_service.id, requirement_id
        )

    async def delete_booking_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> None:
        company_user = require_assigned_company_user(self.current_user)
        booking_service = await self._get_owned_booking_service(
            booking_service_id, company_user.company_id
        )
        await self._get_requirement_for_booking_service(booking_service, requirement_id)
        requirement_file = await self.kp_repository.get_requirement_file(
            booking_service.id, requirement_id
        )
        if requirement_file is None:
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
        if requirement_file is None:
            raise KpServiceRequirementNotFound(
                f"booking_requirement_file:not_found:{booking_service_id}:{requirement_id}"
            )
        return await self.storage_service.generate_download_url(
            requirement_file.stored_file.storage_key,
            requirement_file.stored_file.original_filename,
        )

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
