from collections.abc import Sequence
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.models.kp_event import (
    KpEvent,
    KpEventBooking,
    KpEventNametagBackground,
    NameTag,
)
from app.repositories.base import rel
from app.repositories.kp_repository.base import KpRepositoryBase
from app.schemas.kp import NameTagInput


def _name_tag_options() -> tuple[Any, ...]:
    return (
        selectinload(rel(NameTag.booking)).selectinload(rel(KpEventBooking.company)),
        selectinload(rel(NameTag.booking)).selectinload(rel(KpEventBooking.event)),
    )


class NametagsMixin(KpRepositoryBase):
    async def get_name_tag_by_id(self, name_tag_id: UUID) -> Optional[NameTag]:
        statement = (
            select(NameTag)
            .where(col(NameTag.id) == name_tag_id)
            .options(*_name_tag_options())
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_name_tags_for_event(self, event_id: UUID) -> Sequence[NameTag]:
        return await self._list_name_tags(
            select(NameTag)
            .join(KpEventBooking)
            .where(col(KpEventBooking.event_id) == event_id)
        )

    async def list_name_tags_for_booking(self, booking_id: UUID) -> Sequence[NameTag]:
        return await self._list_name_tags(
            select(NameTag).where(col(NameTag.booking_id) == booking_id)
        )

    async def _list_name_tags(
        self, statement: SelectOfScalar[NameTag]
    ) -> Sequence[NameTag]:
        result = await self.session.execute(
            statement.options(*_name_tag_options()).order_by(
                col(NameTag.last_name).asc(), col(NameTag.first_name).asc()
            )
        )
        return result.scalars().all()

    async def replace_name_tags(
        self, booking: KpEventBooking, name_tags: Sequence[NameTagInput]
    ) -> Sequence[NameTag]:
        async with self.committing():
            await self.hard_delete_where(NameTag, col(NameTag.booking_id) == booking.id)
            for name_tag_input in name_tags:
                name_tag = NameTag(booking_id=booking.id, **name_tag_input.model_dump())
                self._validate_model(name_tag)
                self.session.add(name_tag)
        return await self.list_name_tags_for_booking(booking.id)

    async def get_nametag_background(
        self, event_id: UUID
    ) -> Optional[KpEventNametagBackground]:
        statement = (
            select(KpEventNametagBackground)
            .where(col(KpEventNametagBackground.event_id) == event_id)
            .options(
                selectinload(rel(KpEventNametagBackground.event)),
                selectinload(rel(KpEventNametagBackground.stored_file)),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_nametag_background(
        self,
        event_id: UUID,
        stored_file_id: UUID,
    ) -> KpEventNametagBackground:
        async with self.committing():
            await self.lock_model_by_id(KpEvent, event_id)
            background = await self.get_nametag_background(event_id)
            if background is None:
                background = KpEventNametagBackground(
                    event_id=event_id,
                    stored_file_id=stored_file_id,
                )
            else:
                background.stored_file_id = stored_file_id

            self._validate_model(background)
            self.session.add(background)
        return await self.get_nametag_background(event_id) or background
