from datetime import date
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.decorators import (
    require_confirmed_company,
    require_role,
    require_staff,
)
from app.core.exceptions import (
    KpBookingConfirmationRequiresFinalized,
    KpBookingNotFound,
    KpBookingNotOwned,
    KpBookingStatusTransitionInvalid,
    KpBoothZoneEventMismatch,
    KpBoothZoneNotFound,
    KpNameExists,
    KpRequirementBookingServiceMismatch,
    KpServiceRequirementNotFound,
    KpWaitlistSameZone,
)
from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingUpgradeWaitlist,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
)
from app.models.user import User
from app.repositories.kp_repository import KpRepository
from app.services.storage_service import StorageService


class KpService:
    def __init__(
        self,
        kp_repository: KpRepository,
        storage_service: StorageService,
        current_user: User,
    ):
        self.kp_repository = kp_repository
        self.storage_service = storage_service
        self.current_user = current_user

    async def list_kps(self) -> list[KpEvent]:
        return await self.kp_repository.list_kps()

    async def get_latest_kp(self) -> Optional[KpEvent]:
        return await self.kp_repository.get_latest_kp()

    async def get_event_by_name(self, name: str) -> Optional[KpEvent]:
        return await self.kp_repository.get_by_name(name)

    async def _get_owned_booking(self, booking_id: UUID):
        booking = await self.kp_repository.get_booking_by_id(booking_id)
        if booking is None:
            raise KpBookingNotFound(f"booking_upgrade_waitlist:not_found:{booking_id}")
        if (
            self.current_user.company_id is None
            or booking.company_id != self.current_user.company_id
        ):
            raise KpBookingNotOwned(f"booking_upgrade_waitlist:not_owned:{booking_id}")
        return booking

    async def _get_booking(self, booking_id: UUID) -> KpEventBooking:
        booking = await self.kp_repository.get_booking_by_id(booking_id)
        if booking is None:
            raise KpBookingNotFound(f"booking:not_found:{booking_id}")
        return booking

    async def _get_owned_booking_service(
        self, booking_service_id: UUID
    ) -> KpEventBookingService:
        booking_service = await self.kp_repository.get_booking_service_by_id(
            booking_service_id
        )
        if booking_service is None:
            raise KpBookingNotFound(f"booking_service:not_found:{booking_service_id}")
        if (
            self.current_user.company_id is None
            or booking_service.booking.company_id != self.current_user.company_id
        ):
            raise KpBookingNotOwned(f"booking_service:not_owned:{booking_service_id}")
        return booking_service

    def _ensure_company_status_transition(
        self, booking: KpEventBooking, next_status: KpBookingStatus
    ) -> None:
        if booking.status == next_status:
            return
        allowed_transitions = {
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

    @require_confirmed_company
    async def list_booking_upgrade_waitlist(
        self, booking_id: UUID
    ) -> list[KpEventBookingUpgradeWaitlist]:
        booking = await self._get_owned_booking(booking_id)
        return await self.kp_repository.list_booking_upgrade_waitlist_entries(
            booking.id
        )

    @require_confirmed_company
    async def replace_booking_upgrade_waitlist(
        self, booking_id: UUID, target_booth_zone_ids: list[UUID]
    ) -> list[KpEventBookingUpgradeWaitlist]:
        booking = await self._get_owned_booking(booking_id)

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

    @require_confirmed_company
    async def update_my_booking_status(
        self, booking_id: UUID, status: KpBookingStatus
    ) -> KpEventBooking:
        booking = await self._get_owned_booking(booking_id)
        self._ensure_company_status_transition(booking, status)
        return await self.kp_repository.update_booking(booking=booking, status=status)

    @require_staff
    async def update_booking_booth_number(
        self, booking_id: UUID, booth_nr: int
    ) -> KpEventBooking:
        booking = await self._get_booking(booking_id)
        return await self.kp_repository.update_booking(
            booking=booking, booth_nr=booth_nr
        )

    @require_staff
    async def confirm_booking(self, booking_id: UUID) -> KpEventBooking:
        booking = await self._get_booking(booking_id)
        if booking.status != KpBookingStatus.FINALIZED:
            raise KpBookingConfirmationRequiresFinalized(
                f"booking_confirm:not_finalized:{booking_id}:{booking.status}"
            )
        return await self.kp_repository.update_booking(
            booking=booking, status=KpBookingStatus.CONFIRMED
        )

    async def _get_requirement_for_booking_service(
        self, booking_service: KpEventBookingService, requirement_id: UUID
    ):
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

    @require_confirmed_company
    async def upload_booking_requirement_file(
        self,
        booking_service_id: UUID,
        requirement_id: UUID,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> KpEventBookingServiceFileLink:
        booking_service = await self._get_owned_booking_service(booking_service_id)
        requirement = await self._get_requirement_for_booking_service(
            booking_service, requirement_id
        )
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
        stored_file = await self.kp_repository.upsert_stored_file(
            storage_key=stored_object.key,
            original_filename=filename,
            mime_type=stored_object.mime_type,
            size_bytes=stored_object.size_bytes,
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
        if old_storage_key is not None and old_storage_key != stored_object.key:
            await self.storage_service.delete_object(old_storage_key)
        return requirement_file

    @require_confirmed_company
    async def get_booking_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> KpEventBookingServiceFileLink | None:
        booking_service = await self._get_owned_booking_service(booking_service_id)
        await self._get_requirement_for_booking_service(booking_service, requirement_id)
        return await self.kp_repository.get_requirement_file(
            booking_service.id, requirement_id
        )

    @require_confirmed_company
    async def delete_booking_requirement_file(
        self, booking_service_id: UUID, requirement_id: UUID
    ) -> None:
        booking_service = await self._get_owned_booking_service(booking_service_id)
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

    @require_confirmed_company
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

    @require_role(get_settings().VISIT_KP_PRESIDENT_ROLE)
    async def create_kp(
        self,
        name: str,
        registration_open: date,
        registration_end: date,
        finalization_deadline: date,
        nametags_deadline: date,
        event_date: date,
    ) -> KpEvent:
        existing = await self.kp_repository.get_by_name(name)
        if existing is not None:
            raise KpNameExists(f"create_kp:{name}")

        return await self.kp_repository.create_kp(
            name=name,
            registration_open=registration_open,
            registration_end=registration_end,
            finalization_deadline=finalization_deadline,
            nametags_deadline=nametags_deadline,
            event_date=event_date,
        )
