from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import delete, select, update

from app.models.company import Company, CompanyInvite, KpCompanyProfile
from app.models.user import User
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: AsyncSession):
        super().__init__(Company, session)

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
        statement = (
            select(User)
            .where(User.company_id == company.id)
            .options(selectinload(User.company))
        )
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

    async def get_kp_profile(self, company_id: UUID) -> Optional[KpCompanyProfile]:
        statement = (
            select(KpCompanyProfile)
            .where(KpCompanyProfile.company_id == company_id)
            .options(selectinload(KpCompanyProfile.kp_contact_user))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_kp_profile(
        self,
        company_id: UUID,
        invoice_address: str | None = None,
        shipping_address: str | None = None,
        contact_email: str | None = None,
        kp_contact_user_id: UUID | None = None,
    ) -> KpCompanyProfile:
        try:
            profile = await self.get_kp_profile(company_id)
            if profile is None:
                profile = KpCompanyProfile(company_id=company_id)

            if invoice_address is not None:
                profile.invoice_address = invoice_address
            if shipping_address is not None:
                profile.shipping_address = shipping_address
            if contact_email is not None:
                profile.contact_email = contact_email
            profile.kp_contact_user_id = kp_contact_user_id

            self._validate_model(
                profile,
                exclude={"company", "kp_contact_user"},
            )
            self.session.add(profile)
            await self.session.commit()
            await self.session.refresh(profile)
            return await self.get_kp_profile(company_id) or profile
        except Exception as e:
            await self.session.rollback()
            raise e

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

    async def assign_user(self, user: User, company_id: UUID) -> User:
        try:
            user.company_id = company_id
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user, attribute_names=["company"])
            return user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_invite(
        self,
        token: str,
        company_id: UUID,
        invited_email: str,
        expires_at: datetime,
    ) -> CompanyInvite:
        try:
            invite = CompanyInvite(
                token=token,
                company_id=company_id,
                invited_email=invited_email,
                expires_at=expires_at,
            )
            self._validate_model(invite, exclude={"company"})
            self.session.add(invite)
            await self.session.commit()
            await self.session.refresh(invite)
            return invite
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_invite_by_token(self, token: str) -> Optional[CompanyInvite]:
        statement = select(CompanyInvite).where(CompanyInvite.token == token)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_invite_used(self, invite: CompanyInvite):
        try:
            invite.is_used = True
            self.session.add(invite)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
