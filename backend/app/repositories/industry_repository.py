from collections.abc import Sequence
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.industry import Industry, KpCompanyProfileIndustryLink
from app.repositories.base import BaseRepository


class IndustryRepository(BaseRepository[Industry]):
    def __init__(self, session: AsyncSession):
        super().__init__(Industry, session)

    async def list_industries(self) -> Sequence[Industry]:
        statement = select(Industry).order_by(col(Industry.name).asc())
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Optional[Industry]:
        return await self._get_by_field(col(Industry.name), name)

    async def create_industry(self, name: str) -> Industry:
        try:
            industry = Industry(name=name)
            self._validate_model(industry, exclude={"profile_links", "snapshot_links"})
            self.session.add(industry)
            await self.session.commit()
            await self.session.refresh(industry)
            return industry
        except Exception as e:
            await self.session.rollback()
            raise e

    async def rename_industry(self, industry: Industry, name: str) -> Industry:
        try:
            industry.name = name
            self._validate_model(industry, exclude={"profile_links", "snapshot_links"})
            self.session.add(industry)
            await self.session.commit()
            await self.session.refresh(industry)
            return industry
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_industry(self, industry: Industry) -> None:
        try:
            await self.delete_where(
                KpCompanyProfileIndustryLink,
                col(KpCompanyProfileIndustryLink.industry_id) == industry.id,
            )
            self.delete(industry)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
