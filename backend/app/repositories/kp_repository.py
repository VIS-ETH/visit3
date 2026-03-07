from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.kp_event import KpEvent
from app.repositories.base import BaseRepository


class KpRepository(BaseRepository[KpEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(KpEvent, session)

    async def get_by_id(self, kp_event_id: UUID) -> Optional[KpEvent]:
        return await self._get_by_field(KpEvent.id, kp_event_id)

    async def get_by_year(self, year: int) -> Optional[KpEvent]:
        return await self._get_by_field(KpEvent.year, year)

    async def list_events(self) -> list[KpEvent]:
        statement = select(KpEvent).order_by(KpEvent.year.desc())
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_latest_event(self) -> Optional[KpEvent]:
        statement = select(KpEvent).order_by(KpEvent.year.desc()).limit(1)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_event(
        self,
        year: int,
        registration_open: date,
        registration_end: date,
        event_date: date,
    ) -> KpEvent:
        try:
            event = KpEvent(
                year=year,
                registration_open=registration_open,
                registration_end=registration_end,
                event_date=event_date,
            )
            self.session.add(event)
            await self.session.commit()
            await self.session.refresh(event)
            return event
        except Exception as e:
            await self.session.rollback()
            raise e
