from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.core.dates import utc_now
from app.core.deleted_filter import include_deleted_for
from app.models.company import KpCompanyProfile
from app.models.kp_event import (
    KpEvent,
    KpEventBanner,
    KpEventBannerVariant,
    KpEventBookingServiceFileLink,
    KpEventBoothZone,
    KpEventNametagBackground,
    KpEventService,
)
from app.models.storage import StoredFile
from app.models.venue import KpVenueLayout
from app.repositories.base import rel
from app.repositories.kp_repository.base import KpRepositoryBase

STORED_FILE_REFERENCES = (
    (KpEventBookingServiceFileLink, KpEventBookingServiceFileLink.stored_file_id),
    (KpEventNametagBackground, KpEventNametagBackground.stored_file_id),
    (KpEvent, KpEvent.booklet_background_stored_file_id),
    (KpEventService, KpEventService.image_stored_file_id),
    (KpEventBannerVariant, KpEventBannerVariant.stored_file_id),
    (KpCompanyProfile, KpCompanyProfile.logo_stored_file_id),
    (KpVenueLayout, KpVenueLayout.background_stored_file_id),
    (KpEventBoothZone, KpEventBoothZone.layout_stored_file_id),
)


class FilesMixin(KpRepositoryBase):
    async def set_booklet_background(
        self, event: KpEvent, stored_file_id: UUID | None
    ) -> KpEvent:
        async with self.committing():
            event.booklet_background_stored_file_id = stored_file_id
            self.session.add(event)
        await self.session.refresh(event)
        return event

    async def count_events_with_booklet_background(self, stored_file_id: UUID) -> int:
        statement = select(func.count(col(KpEvent.id))).where(
            col(KpEvent.booklet_background_stored_file_id) == stored_file_id
        )
        return (await self.session.execute(statement)).scalar_one()

    async def create_banner(
        self, width: int, height: int, variants: Sequence[tuple[int, StoredFile]]
    ) -> KpEventBanner:
        async with self.committing():
            banner = KpEventBanner(width=width, height=height)
            self.session.add(banner)
            for variant_width, stored_file in variants:
                self.session.add(stored_file)
                self.session.add(
                    KpEventBannerVariant(
                        banner_id=banner.id,
                        width=variant_width,
                        stored_file_id=stored_file.id,
                    )
                )
        loaded = await self.get_banner(banner.id)
        if loaded is None:
            raise LookupError(f"create_banner:{banner.id}")
        return loaded

    async def get_banner(self, banner_id: UUID) -> KpEventBanner | None:
        statement = (
            select(KpEventBanner)
            .where(col(KpEventBanner.id) == banner_id)
            .options(
                selectinload(rel(KpEventBanner.variants)).selectinload(
                    rel(KpEventBannerVariant.stored_file)
                )
            )
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def set_event_banner(self, event: KpEvent, banner_id: UUID | None) -> KpEvent:
        async with self.committing():
            event.banner_id = banner_id
            self.session.add(event)
        await self.session.refresh(event)
        return event

    async def count_events_with_banner(self, banner_id: UUID) -> int:
        statement = select(func.count(col(KpEvent.id))).where(
            col(KpEvent.banner_id) == banner_id
        )
        return (await self.session.execute(statement)).scalar_one()

    async def delete_banner(
        self, banner: KpEventBanner, variants: Sequence[KpEventBannerVariant]
    ) -> None:
        async with self.committing():
            for variant in variants:
                stored_file = variant.stored_file
                await self.session.delete(variant)
                await self.session.flush()
                await self.session.delete(stored_file)
            if len(variants) == len(banner.variants):
                await self.session.delete(banner)

    async def list_orphaned_stored_files(
        self, max_age_hours: int
    ) -> Sequence[StoredFile]:
        cutoff = utc_now() - timedelta(hours=max_age_hours)
        statement = select(StoredFile)
        for model, stored_file_id in STORED_FILE_REFERENCES:
            statement = statement.outerjoin(
                model, col(stored_file_id) == col(StoredFile.id)
            )
        statement = statement.where(
            and_(
                *(col(model.id).is_(None) for model, _ in STORED_FILE_REFERENCES),
                col(StoredFile.updated_at) < cutoff,
            )
        )
        result = await self.session.execute(include_deleted_for(statement, StoredFile))
        return result.scalars().all()
