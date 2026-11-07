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
        async with self.committing():
            industry = Industry(name=name)
            self._validate_model(industry)
            self.session.add(industry)
        await self.session.refresh(industry)
        return industry

    async def rename_industry(self, industry: Industry, name: str) -> Industry:
        async with self.committing():
            industry.name = name
            self._validate_model(industry)
            self.session.add(industry)
        await self.session.refresh(industry)
        return industry

    async def delete_industry(self, industry: Industry) -> None:
        async with self.committing():
            await self.delete_where(
                KpCompanyProfileIndustryLink,
                col(KpCompanyProfileIndustryLink.industry_id) == industry.id,
            )
            self.delete(industry)
