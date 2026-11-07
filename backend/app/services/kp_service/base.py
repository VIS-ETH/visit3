from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import (
    CompanyProfileIncomplete,
    CompanyProfileUnconfirmed,
    KpBookingNotFound,
    KpBookingNotOwned,
    KpBookingReadonly,
    KpBookingZoneLocked,
    KpBoothZoneAtCapacity,
    KpBoothZoneEventMismatch,
    KpBoothZoneNotFound,
    KpFinalizationDeadlinePassed,
    KpOfferPending,
    KpServiceEventMismatch,
    KpServiceNotFound,
    KpZoneRegistrationClosed,
)
from app.models.company import BOOKING_REQUIRED_PROFILE_FIELDS, KpCompanyProfile
from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBoothZone,
    KpEventService,
)
from app.models.user import User
from app.repositories.kp_repository import KpRepository
from app.services.booking_notifier import BookingNotifier, SilentBookingNotifier
from app.services.download_urls import DownloadUrls
from app.services.event_lookup import require_event
from app.services.registration_exceptions import has_registration_exception
from app.services.storage_service import StorageService
from app.services.stored_files import StoredFiles
from app.services.waitlist_promotion import promote_waitlist


class KpServiceBase:
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
        self.stored_files = StoredFiles(storage_service, kp_repository)
        self.current_user = current_user
        self.notifier = notifier or SilentBookingNotifier()
        self.settings = get_settings()

    async def _promote_waitlist(self, event_id: UUID, booth_zone_id: UUID) -> None:
        await promote_waitlist(
            self.kp_repository, self.notifier, event_id, booth_zone_id
        )

    async def _get_event(self, event_id: UUID) -> KpEvent:
        return await require_event(
            self.kp_repository, event_id, f"event:not_found:{event_id}"
        )

    async def _get_event_booth_zone(
        self, booth_zone_id: UUID, event_id: UUID, context: str
    ) -> KpEventBoothZone:
        zone = await self.kp_repository.get_booth_zone_by_id(booth_zone_id)
        if zone is None:
            raise KpBoothZoneNotFound(f"{context}:zone_not_found:{booth_zone_id}")
        if zone.event_id != event_id:
            raise KpBoothZoneEventMismatch(
                f"{context}:zone_event_mismatch:{booth_zone_id}"
            )
        return zone

    async def _related_service(
        self, event_id: UUID, service_id: UUID, context: str
    ) -> KpEventService:
        related = await self.kp_repository.get_service_by_id(service_id)
        if related is None:
            raise KpServiceNotFound(f"{context}:service_not_found:{service_id}")
        if related.event_id != event_id:
            raise KpServiceEventMismatch(
                f"{context}:service_event_mismatch:{service_id}"
            )
        return related

    async def _load_booking(
        self, booking_id: UUID, lock: bool
    ) -> KpEventBooking | None:
        if lock:
            return await self.kp_repository.lock_booking(booking_id)
        return await self.kp_repository.get_booking_by_id(booking_id)

    async def _get_booking(
        self, booking_id: UUID, lock: bool = False
    ) -> KpEventBooking:
        booking = await self._load_booking(booking_id, lock)
        if booking is None:
            raise KpBookingNotFound(f"booking:not_found:{booking_id}")
        return booking

    async def _get_owned_booking(
        self, booking_id: UUID, company_id: UUID, context: str, lock: bool = False
    ) -> KpEventBooking:
        booking = await self._load_booking(booking_id, lock)
        if booking is None:
            raise KpBookingNotFound(f"{context}:not_found:{booking_id}")
        if booking.company_id != company_id:
            raise KpBookingNotOwned(f"{context}:not_owned:{booking_id}")
        return booking

    async def _get_booking_service(
        self, booking_service_id: UUID
    ) -> KpEventBookingService:
        booking_service = await self.kp_repository.get_booking_service_by_id(
            booking_service_id
        )
        if booking_service is None:
            raise KpBookingNotFound(f"booking_service:not_found:{booking_service_id}")
        return booking_service

    async def _get_owned_booking_service(
        self, booking_service_id: UUID, company_id: UUID
    ) -> KpEventBookingService:
        booking_service = await self._get_booking_service(booking_service_id)
        if booking_service.booking.company_id != company_id:
            raise KpBookingNotOwned(f"booking_service:not_owned:{booking_service_id}")
        return booking_service

    async def _is_registration_open(self, event: KpEvent, company_id: UUID) -> bool:
        return event.is_registration_open() or await has_registration_exception(
            self.kp_repository, event.id, company_id
        )

    async def _ensure_zone_registration_open(
        self, zone: KpEventBoothZone, company_id: UUID, context: str
    ) -> None:
        if zone.registration_open or await has_registration_exception(
            self.kp_repository, zone.event_id, company_id
        ):
            return
        raise KpZoneRegistrationClosed(f"{context}:zone_closed:{zone.id}:{company_id}")

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

    async def _lock_zone_until_booking_is_inserted(
        self, booth_zone_id: UUID, context: str = "register_booking"
    ) -> KpEventBoothZone:
        locked_zone = await self.kp_repository.lock_booth_zone(booth_zone_id)
        if locked_zone is None:
            raise KpBoothZoneNotFound(
                f"{context}:locked_zone_not_found:{booth_zone_id}"
            )
        return locked_zone

    async def _ensure_zone_not_full(
        self, event_id: UUID, zone: KpEventBoothZone, context: str
    ) -> None:
        count = await self.kp_repository.count_active_bookings_for_zone(
            event_id, zone.id
        )
        if count >= zone.capacity:
            raise KpBoothZoneAtCapacity(f"{context}:at_capacity:{zone.id}")

    def _ensure_active_booking(self, booking: KpEventBooking, context: str) -> None:
        if not booking.is_active:
            raise KpBookingReadonly(f"{context}:readonly:{booking.id}:{booking.status}")
        if booking.status == KpBookingStatus.OFFERED:
            raise KpOfferPending(f"{context}:offer_pending:{booking.id}")

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
        self._ensure_active_booking(booking, context)
        self._ensure_finalization_deadline_open(booking, context)

    def _ensure_zone_unlocked(self, booking: KpEventBooking, context: str) -> None:
        if booking.status == KpBookingStatus.CONFIRMED:
            raise KpBookingZoneLocked(f"{context}:zone_locked:{booking.id}")
