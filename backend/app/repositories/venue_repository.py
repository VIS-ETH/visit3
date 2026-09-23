from collections.abc import Sequence
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.kp_event import KpEventBoothZone
from app.models.venue import KpVenueBooth, KpVenueLayout, KpVenueZoneShape
from app.repositories.base import BaseRepository, rel
from app.schemas.venue import (
    CreateVenueLayoutInput,
    UpdateVenueLayoutInput,
    VenueBoothInput,
    VenueZoneShapeInput,
)

LAYOUT_RELATIONSHIPS = {"background_stored_file", "zone_shapes", "booths"}
SHAPE_RELATIONSHIPS = {"layout", "booth_zone"}


class VenueRepository(BaseRepository[KpVenueLayout]):
    def __init__(self, session: AsyncSession):
        super().__init__(KpVenueLayout, session)

    def _layout_select(self):
        return (
            select(KpVenueLayout)
            .options(selectinload(rel(KpVenueLayout.background_stored_file)))
            .order_by(col(KpVenueLayout.order).asc(), col(KpVenueLayout.name).asc())
        )

    async def list_layouts(self, event_id: UUID) -> Sequence[KpVenueLayout]:
        statement = self._layout_select().where(col(KpVenueLayout.event_id) == event_id)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_active_layouts(self, event_id: UUID) -> Sequence[KpVenueLayout]:
        statement = self._layout_select().where(
            col(KpVenueLayout.event_id) == event_id,
            col(KpVenueLayout.is_active).is_(True),
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_layout_by_id(self, layout_id: UUID) -> Optional[KpVenueLayout]:
        statement = (
            self._layout_select()
            .where(col(KpVenueLayout.id) == layout_id)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_layout_by_name(
        self, event_id: UUID, name: str
    ) -> Optional[KpVenueLayout]:
        statement = self._layout_select().where(
            col(KpVenueLayout.event_id) == event_id,
            col(KpVenueLayout.name) == name,
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def create_layout(
        self, event_id: UUID, create_layout_input: CreateVenueLayoutInput
    ) -> KpVenueLayout:
        try:
            layout = KpVenueLayout(
                **create_layout_input.model_dump(), event_id=event_id
            )
            self._validate_model(layout, exclude=LAYOUT_RELATIONSHIPS)
            self.session.add(layout)
            await self.session.commit()
            return await self.get_layout_by_id(layout.id) or layout
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_layout(
        self, layout: KpVenueLayout, update_layout_input: UpdateVenueLayoutInput
    ) -> KpVenueLayout:
        try:
            layout.sqlmodel_update(update_layout_input.model_dump(exclude_unset=True))
            self._validate_model(layout, exclude=LAYOUT_RELATIONSHIPS)
            self.session.add(layout)
            await self.session.commit()
            return await self.get_layout_by_id(layout.id) or layout
        except Exception as e:
            await self.session.rollback()
            raise e

    async def set_layout_background_stored_file_id(
        self, layout: KpVenueLayout, stored_file_id: UUID | None
    ) -> KpVenueLayout:
        try:
            layout.background_stored_file_id = stored_file_id
            self.session.add(layout)
            await self.session.commit()
            return await self.get_layout_by_id(layout.id) or layout
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_layout(self, layout: KpVenueLayout) -> None:
        try:
            await self.delete_where(
                KpVenueZoneShape, col(KpVenueZoneShape.layout_id) == layout.id
            )
            await self.delete_where(
                KpVenueBooth, col(KpVenueBooth.layout_id) == layout.id
            )
            layout.background_stored_file_id = None
            self.delete(layout)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def list_zone_shapes(
        self, layout_ids: Sequence[UUID]
    ) -> Sequence[KpVenueZoneShape]:
        statement = (
            select(KpVenueZoneShape)
            .join(
                KpEventBoothZone,
                col(KpEventBoothZone.id) == col(KpVenueZoneShape.booth_zone_id),
            )
            .where(
                col(KpVenueZoneShape.layout_id).in_(layout_ids),
                col(KpEventBoothZone.deleted_at).is_(None),
            )
            .order_by(col(KpVenueZoneShape.created_at).asc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_booths(self, layout_ids: Sequence[UUID]) -> Sequence[KpVenueBooth]:
        statement = (
            select(KpVenueBooth)
            .join(
                KpEventBoothZone,
                col(KpEventBoothZone.id) == col(KpVenueBooth.booth_zone_id),
            )
            .where(
                col(KpVenueBooth.layout_id).in_(layout_ids),
                col(KpEventBoothZone.deleted_at).is_(None),
            )
            .order_by(col(KpVenueBooth.booth_nr).asc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def replace_zone_shapes(
        self, layout: KpVenueLayout, shapes: Sequence[VenueZoneShapeInput]
    ) -> Sequence[KpVenueZoneShape]:
        try:
            await self.hard_delete_where(
                KpVenueZoneShape, col(KpVenueZoneShape.layout_id) == layout.id
            )
            for shape_input in shapes:
                shape = KpVenueZoneShape(
                    layout_id=layout.id,
                    booth_zone_id=shape_input.booth_zone_id,
                    shape=shape_input.shape.model_dump(mode="json"),
                    label_position=(
                        list(shape_input.label_position)
                        if shape_input.label_position is not None
                        else None
                    ),
                )
                self._validate_model(shape, exclude=SHAPE_RELATIONSHIPS)
                self.session.add(shape)
            await self.session.commit()
            return await self.list_zone_shapes([layout.id])
        except Exception as e:
            await self.session.rollback()
            raise e

    async def replace_booths(
        self, layout: KpVenueLayout, booths: Sequence[VenueBoothInput]
    ) -> Sequence[KpVenueBooth]:
        try:
            await self.hard_delete_where(
                KpVenueBooth, col(KpVenueBooth.layout_id) == layout.id
            )
            for booth_input in booths:
                booth = KpVenueBooth(layout_id=layout.id, **booth_input.model_dump())
                self._validate_model(booth, exclude=SHAPE_RELATIONSHIPS)
                self.session.add(booth)
            await self.session.commit()
            return await self.list_booths([layout.id])
        except Exception as e:
            await self.session.rollback()
            raise e
