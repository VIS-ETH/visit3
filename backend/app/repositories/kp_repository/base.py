from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.core.deleted_filter import include_deleted_for
from app.models.company import Company, KpCompanyProfile
from app.models.industry import Industry
from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpBookingCompanyDetailsIndustryLink,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventService,
    KpEventServiceRequirement,
)
from app.repositories.base import BaseRepository, rel
from app.repositories.stored_file_queries import StoredFileQueries


def booth_zone_options() -> tuple[Any, ...]:
    return (
        selectinload(rel(KpEventBoothZone.included_services)),
        selectinload(rel(KpEventBoothZone.layout_stored_file)),
    )


class KpRepositoryBase(BaseRepository[KpEvent], StoredFileQueries):
    def __init__(self, session: AsyncSession):
        super().__init__(KpEvent, session)

    def _booking_select(self):
        statement = select(KpEventBooking).options(
            selectinload(rel(KpEventBooking.event)),
            selectinload(rel(KpEventBooking.booth_zone)).selectinload(
                rel(KpEventBoothZone.included_services)
            ),
            selectinload(rel(KpEventBooking.booth_zone)).selectinload(
                rel(KpEventBoothZone.layout_stored_file)
            ),
            selectinload(rel(KpEventBooking.name_tags)),
            selectinload(rel(KpEventBooking.company)).selectinload(
                rel(Company.kp_profile)
            ),
            selectinload(rel(KpEventBooking.company))
            .selectinload(rel(Company.kp_profile))
            .selectinload(rel(KpCompanyProfile.kp_contact_user)),
            selectinload(rel(KpEventBooking.company)).selectinload(rel(Company.users)),
            selectinload(rel(KpEventBooking.services))
            .selectinload(rel(KpEventBookingService.service))
            .selectinload(rel(KpEventService.requirements)),
            selectinload(rel(KpEventBooking.services))
            .selectinload(rel(KpEventBookingService.service))
            .selectinload(rel(KpEventService.image_stored_file)),
            selectinload(rel(KpEventBooking.services))
            .selectinload(rel(KpEventBookingService.requirement_file_links))
            .selectinload(rel(KpEventBookingServiceFileLink.requirement)),
            selectinload(rel(KpEventBooking.services))
            .selectinload(rel(KpEventBookingService.requirement_file_links))
            .selectinload(rel(KpEventBookingServiceFileLink.stored_file)),
            selectinload(rel(KpEventBooking.upgrade_waitlist_entries))
            .selectinload(rel(KpEventBookingUpgradeWaitlist.target_booth_zone))
            .selectinload(rel(KpEventBoothZone.included_services)),
            selectinload(rel(KpEventBooking.upgrade_waitlist_entries))
            .selectinload(rel(KpEventBookingUpgradeWaitlist.target_booth_zone))
            .selectinload(rel(KpEventBoothZone.layout_stored_file)),
            selectinload(rel(KpEventBooking.company_details))
            .selectinload(rel(KpBookingCompanyDetails.industry_links))
            .selectinload(rel(KpBookingCompanyDetailsIndustryLink.industry)),
        )
        return include_deleted_for(
            statement.execution_options(populate_existing=True),
            KpEventBoothZone,
            Company,
            KpEventService,
            KpEventServiceRequirement,
            Industry,
        )

    def _booth_zone_select(self):
        return (
            select(KpEventBoothZone)
            .options(*booth_zone_options())
            .execution_options(populate_existing=True)
        )

    async def get_booking_by_id(self, booking_id: UUID) -> Optional[KpEventBooking]:
        statement = self._booking_select().where(col(KpEventBooking.id) == booking_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
