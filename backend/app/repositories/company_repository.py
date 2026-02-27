from typing import List, Optional
from sqlmodel import select, delete, update
from sqlalchemy.orm import selectinload
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
        statement = select(User).where(User.company_id == company.id)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_companies(self) -> List[Company]:
        statement = select(Company)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_companies_with_users(self) -> List[Company]:
        statement = select(Company).options(selectinload(Company.users))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def delete_company_with_users(self, company: Company):
        try:
            delete_users_statement = delete(User).where(User.company_id == company.id)
            await self.session.execute(delete_users_statement)
            await self.session.delete(company)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_company_keep_users(self, company: Company):
        try:
            unassign_users_statement = (
                update(User)
                .where(User.company_id == company.id)
                .values(company_id=None)
            )
            await self.session.execute(unassign_users_statement)
            await self.session.delete(company)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_company_name(self, company: Company, name: str) -> Company:
        try:
            company.name = name
            self.session.add(company)
            await self.session.commit()
            await self.session.refresh(company)
            return company
        except Exception as e:
            await self.session.rollback()
            raise e
