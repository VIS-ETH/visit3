from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.kp_event import (
    KpEventBooking,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
)
from app.repositories.base import rel
from app.repositories.kp_repository.base import KpRepositoryBase

WAITLIST_ORDER = (
    col(KpEventBookingUpgradeWaitlist.priority_rank).asc().nulls_last(),
    col(KpEventBookingUpgradeWaitlist.created_at).asc(),
)


class WaitlistMixin(KpRepositoryBase):
    async def list_booking_upgrade_waitlist_entries(
        self, booking_id: UUID
    ) -> Sequence[KpEventBookingUpgradeWaitlist]:
        statement = (
            select(KpEventBookingUpgradeWaitlist)
            .where(col(KpEventBookingUpgradeWaitlist.booking_id) == booking_id)
            .order_by(*WAITLIST_ORDER)
            .options(
                selectinload(
                    rel(KpEventBookingUpgradeWaitlist.target_booth_zone)
                ).selectinload(rel(KpEventBoothZone.included_services)),
                selectinload(
                    rel(KpEventBookingUpgradeWaitlist.target_booth_zone)
                ).selectinload(rel(KpEventBoothZone.layout_stored_file)),
                selectinload(rel(KpEventBookingUpgradeWaitlist.booking)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_waitlist_entries_for_zone(
        self, booth_zone_id: UUID
    ) -> Sequence[KpEventBookingUpgradeWaitlist]:
        statement = (
            select(KpEventBookingUpgradeWaitlist)
            .where(
                col(KpEventBookingUpgradeWaitlist.target_booth_zone_id) == booth_zone_id
            )
            .order_by(*WAITLIST_ORDER)
            .options(selectinload(rel(KpEventBookingUpgradeWaitlist.booking)))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def delete_waitlist_entry(self, entry: KpEventBookingUpgradeWaitlist) -> None:
        async with self.committing():
            await self.session.delete(entry)

    async def replace_booking_upgrade_waitlist_entries(
        self,
        booking: KpEventBooking,
        target_booth_zone_ids: list[UUID],
    ) -> Sequence[KpEventBookingUpgradeWaitlist]:
        async with self.committing():
            statement = select(KpEventBookingUpgradeWaitlist).where(
                col(KpEventBookingUpgradeWaitlist.booking_id) == booking.id
            )
            result = await self.session.execute(statement)
            removed_entries = {
                entry.target_booth_zone_id: entry for entry in result.scalars().all()
            }

            for priority_rank, target_booth_zone_id in enumerate(
                target_booth_zone_ids, start=1
            ):
                entry = removed_entries.pop(
                    target_booth_zone_id, None
                ) or KpEventBookingUpgradeWaitlist(
                    booking_id=booking.id,
                    target_booth_zone_id=target_booth_zone_id,
                )
                entry.priority_rank = priority_rank
                self._validate_model(entry)
                self.session.add(entry)

            for entry in removed_entries.values():
                await self.session.delete(entry)
        return await self.list_booking_upgrade_waitlist_entries(booking.id)
