import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, update

from app.core.utils import normalize_email
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    def _validate_user(self, user: User) -> None:
        self._validate_model(
            user,
            exclude={"roles", "company"},
        )

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

    async def get_by_email(self, email: str):
        return await self._get_by_field(User.email, normalize_email(email))

    async def get_by_sub(self, sub: str):
        return await self._get_by_field(User.sub, sub)

    async def get_by_sub_or_email(
        self, sub: str | None, email: str | None
    ) -> User | None:
        """Get a user by sub first, then fallback to email if needed."""
        if sub is not None:
            user = await self.get_by_sub(sub)
            if user is not None:
                return user
        if email is not None:
            return await self.get_by_email(email)
        return None

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

    async def update_company_user(
        self,
        user: User,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        phone_number: str | None = None,
        company_id: uuid.UUID | None = None,
    ) -> User:
        try:
            if email is not None:
                user.email = email
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if phone_number is not None:
                user.phone_number = phone_number
            if company_id is not None:
                user.company_id = company_id

            self._validate_user(user)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user, attribute_names=["company"])
            return user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_user(self, user: User):
        try:
            self._validate_user(user)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_or_update_user(self, user: User):
        try:
            self._validate_user(user)
            db_user = await self.get_by_sub_or_email(user.sub, user.email)
            if db_user is None:
                return await self.create_user(user)
            else:
                update_data = user.model_dump(exclude={"id", "roles", "company"})
                for key, value in update_data.items():
                    setattr(db_user, key, value)

                await self.load_user_roles(db_user)
                db_user.roles = user.roles
                self._validate_user(db_user)
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
