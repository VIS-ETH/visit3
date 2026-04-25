from datetime import date
from typing import Optional
from uuid import UUID

from app.core.config import get_settings
from app.core.decorators import require_confirmed_company, require_role
from app.core.exceptions import (
    KpBookingNotFound,
    KpBookingNotOwned,
    KpBoothZoneEventMismatch,
    KpBoothZoneNotFound,
    KpNameExists,
    KpWaitlistSameZone,
)
from app.models.kp_event import KpEvent, KpEventBookingUpgradeWaitlist
from app.models.user import User
from app.repositories.kp_repository import KpRepository


class KpService:
    def __init__(
        self,
        kp_repository: KpRepository,
        current_user: User,
    ):
        self.kp_repository = kp_repository
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
