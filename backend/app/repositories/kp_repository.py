from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.kp_event import KpEvent, KpEventCompanyLink
from app.repositories.base import BaseRepository


class KpRepository(BaseRepository[KpEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(KpEvent, session)

    async def get_by_id(self, kp_event_id: UUID) -> Optional[KpEvent]:
        return await self._get_by_field(KpEvent.id, kp_event_id)

    async def get_by_year(self, year: int) -> Optional[KpEvent]:
        return await self._get_by_field(KpEvent.year, year)

    async def list_kps(self) -> list[KpEvent]:
        statement = select(KpEvent).order_by(KpEvent.year.desc())
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_latest_kp(self) -> Optional[KpEvent]:
        statement = select(KpEvent).order_by(KpEvent.year.desc()).limit(1)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_kp(
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

    async def register_company_for_kp(self, company_id: UUID, event_id: UUID):
        try:
            link = KpEventCompanyLink(event_id=event_id, company_id=company_id)
            self.session.add(link)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def deregister_company_from_kp(self, company_id: UUID, event_id: UUID):
        try:
            statement = select(KpEventCompanyLink).where(
                KpEventCompanyLink.event_id == event_id,
                KpEventCompanyLink.company_id == company_id,
            )
            result = await self.session.execute(statement)
            link = result.scalar_one_or_none()
            if link is not None:
                link.deleted = True
                self.session.add(link)
                await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def list_companies_for_kp(self, event_id: UUID) -> list[UUID]:
        statement = select(KpEventCompanyLink).where(
            KpEventCompanyLink.event_id == event_id, KpEventCompanyLink.deleted == False
        )
        result = await self.session.execute(statement)
        return [link.company_id for link in result.scalars().all()]
