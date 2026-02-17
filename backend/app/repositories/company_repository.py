from typing import List, Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company import Company
from app.models.user import User
from app.repositories.base import BaseRepository

class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: AsyncSession):
        super().__init__(Company, session)

    async def get_by_id(self, company_id) -> Optional[Company]:
        return await self._get_by_field(Company.id, company_id)

    async def create_company(self, name: str) -> Company:
        try:
            company = Company(name=name)
            self.session.add(company)
            await self.session.commit()
            await self.session.refresh(company)
            return company
        except Exception as e:
            await self.session.rollback()
            raise e
        
    async def get_by_name(self, name: str) -> Optional[Company]:
        return await self._get_by_field(Company.name, name)

    async def get_users(self, company: Company) -> List[User]:
        stmt = select(User).where(User.company_id == company.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_companies(self) -> List[Company]:
        stmt = select(Company)
        result = await self.session.execute(stmt)
        return result.scalars().all()
