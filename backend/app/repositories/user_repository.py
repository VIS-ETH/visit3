from datetime import datetime, timezone
from typing import List
import uuid
from sqlalchemy.orm import selectinload
from sqlmodel import update, select
from app.core.utils import normalize_email
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_admins(self) -> list[User]:
        statement = select(User).where(User.is_admin == True)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_staff(self) -> list[User]:
        statement = select(User).where(User.is_staff == True)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_company_users(self) -> list[User]:
        statement = (
            select(User)
            .where(User.is_company == True)
            .options(selectinload(User.company))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def load_user_company(self, user: User) -> User:
        await self.session.refresh(user, attribute_names=["company"])
        return user

    async def load_user_roles(self, user: User) -> User:
        await self.session.refresh(user, attribute_names=["roles"])
        return user

    async def get_users(self):
        statement = select(User)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_by_id(self, user_id: uuid.UUID):
        return await self._get_by_field(User.id, user_id)

    async def get_by_email(self, email: str):
        return await self._get_by_field(User.email, normalize_email(email))

    async def get_by_sub(self, sub: str):
        return await self._get_by_field(User.sub, sub)

    async def get_unconfirmed_users(self) -> List[User]:
        statement = (
            select(User)
            .where(User.user_confirmed == False)
            .options(selectinload(User.company))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def confirm_user(self, user: User):
        try:
            user.user_confirmed = True
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete_user(self, user: User):
        try:
            await self.session.delete(user)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_user_profile(
        self,
        user: User,
        first_name: str | None,
        last_name: str | None,
        phone_number: str | None,
    ) -> User:
        try:
            user.first_name = first_name
            user.last_name = last_name
            user.phone_number = phone_number

            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user, attribute_names=["company"])
            return user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_user(self, user: User):
        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_or_update_user(self, user: User):
        try:
            db_user = await self.get_by_email(user.email)
            if db_user is None:
                return await self.create_user(user)
            else:
                update_data = user.model_dump(exclude={"id", "roles", "company"})
                for key, value in update_data.items():
                    setattr(db_user, key, value)

                await self.load_user_roles(db_user)
                db_user.roles = user.roles
                self.session.add(db_user)
                await self.session.commit()
                await self.session.refresh(db_user)
                return db_user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_password(self, user_id: uuid.UUID, new_password_hash: str):
        try:
            await self.session.execute(
                update(User)
                .where(User.id == user_id)
                .values(password=new_password_hash)
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def confirm_email(self, user: User):
        try:
            user.email_confirmed = True
            self.session.add(user)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
