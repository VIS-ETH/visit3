from collections.abc import Sequence
from uuid import UUID

from app.core.auth_context import require_assigned_company_user, require_staff_user
from app.core.exceptions import KpWaitlistSameZone, KpWaitlistZoneHasCapacity
from app.models.kp_event import (
    KpBookingStatus,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
)
from app.schemas.kp import (
    BookingUpgradeWaitlistEntryResult,
    StaffBookingUpgradeWaitlistEntryResult,
)
from app.services.booth_zone_view import free_spots
from app.services.kp_service.responses import ResponsesMixin


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


class WaitlistMixin(ResponsesMixin):
    async def _free_spots_in_zone(self, zone: KpEventBoothZone) -> int:
        taken = await self.kp_repository.count_active_bookings_for_zone(
            zone.event_id, zone.id
        )
        return free_spots(zone.capacity, taken)

    async def _build_staff_waitlist_entry(
        self, entry: KpEventBookingUpgradeWaitlist
    ) -> StaffBookingUpgradeWaitlistEntryResult:
        zone = entry.target_booth_zone
        queue = await self.kp_repository.list_waitlist_entries_for_zone(zone.id)
        available_spots = await self._free_spots_in_zone(zone)
        return StaffBookingUpgradeWaitlistEntryResult(
            id=entry.id,
            booking_id=entry.booking_id,
            target_booth_zone_id=entry.target_booth_zone_id,
            priority_rank=entry.priority_rank,
            target_booth_zone=await self._build_staff_booth_zone_response(zone),
            is_full=available_spots == 0,
            available_spots=available_spots,
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
            target_zone = await self._get_event_booth_zone(
                target_booth_zone_id, booking.event_id, "booking_upgrade_waitlist"
            )
            if target_zone.id == booking.booth_zone_id:
                raise KpWaitlistSameZone(
                    f"booking_upgrade_waitlist:same_zone:{booking_id}:{target_zone.id}"
                )
            await self._ensure_zone_registration_open(
                target_zone, company_user.company_id, "booking_upgrade_waitlist"
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
