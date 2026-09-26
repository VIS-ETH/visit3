import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select
from sqlmodel import col, or_, select

from app.core.utils import normalize_email
from app.models.company import Company, KpCompanyProfile
from app.models.user import Role, User
from app.repositories.base import BaseRepository, rel
from app.schemas.user import UserFilter, UserProfileFieldsInput


def _filter_conditions(user_filter: UserFilter) -> list[ColumnElement[bool]]:
    if user_filter is UserFilter.UNCONFIRMED:
        return [col(User.user_confirmed).is_(False)]
    if user_filter is UserFilter.COMPANY:
        return [col(User.is_company).is_(True)]
    if user_filter is UserFilter.STAFF:
        return [col(User.is_staff).is_(True)]
    return []


def _search_conditions(query: str | None) -> list[ColumnElement[bool]]:
    term = (query or "").strip()
    if not term:
        return []
    return [
        or_(
            col(User.email).icontains(term, autoescape=True),
            col(User.first_name).icontains(term, autoescape=True),
            col(User.last_name).icontains(term, autoescape=True),
            col(Company.name).icontains(term, autoescape=True),
        )
    ]


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    def _validate_user(self, user: User) -> None:
        self._validate_model(
            user,
            exclude={"roles", "company"},
        )

    async def get_admins(self) -> Sequence[User]:
        statement = select(User).where(User.is_admin == True)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_staff(self) -> Sequence[User]:
        statement = select(User).where(User.is_staff == True)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_company_users(self) -> Sequence[User]:
        statement = (
            select(User)
            .where(User.is_company == True)
            .options(selectinload(rel(User.company)))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def load_user_company(self, user: User) -> User:
        statement = (
            select(User)
            .where(col(User.id) == user.id)
            .options(selectinload(rel(User.company)))
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() or user

    async def load_user_roles(self, user: User) -> User:
        statement = (
            select(User)
            .where(col(User.id) == user.id)
            .options(selectinload(rel(User.roles)))
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() or user

    async def get_users(self) -> Sequence[User]:
        statement = select(User)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(col(User.email) == normalize_email(email))
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_sub(self, sub: str) -> User | None:
        statement = select(User).where(col(User.sub) == sub)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    def _searchable_users(
        self, query: str | None, user_filter: UserFilter
    ) -> Select[tuple[User]]:
        return (
            select(User)
            .outerjoin(
                Company,
                (col(User.company_id) == col(Company.id)) & self._not_deleted(Company),
            )
            .where(
                self._not_deleted(User),
                *_filter_conditions(user_filter),
                *_search_conditions(query),
            )
        )

    async def count_users_matching(
        self, query: str | None, user_filter: UserFilter
    ) -> int:
        statement = self._searchable_users(query, user_filter).with_only_columns(
            func.count(col(User.id))
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def search_users(
        self, query: str | None, user_filter: UserFilter, offset: int, limit: int
    ) -> Sequence[User]:
        statement = (
            self._searchable_users(query, user_filter)
            .options(selectinload(rel(User.company)))
            .execution_options(populate_existing=True)
            .order_by(col(User.email))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_unconfirmed_users(self) -> Sequence[User]:
        statement = (
            select(User)
            .where(col(User.user_confirmed) == False)
            .options(selectinload(rel(User.company)))
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
            await self.update_where(
                KpCompanyProfile,
                col(KpCompanyProfile.kp_contact_user_id) == user.id,
                kp_contact_user_id=None,
            )
            self.delete(user)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_user(self, user: User, update: UserProfileFieldsInput) -> User:
        try:
            changes = update.model_dump(exclude_unset=True)
            if "company_id" in changes and changes["company_id"] != user.company_id:
                changes["new_in_company_since"] = (
                    datetime.now(timezone.utc)
                    if changes["company_id"] is not None
                    else None
                )
            email = changes.get("email")
            email_changed = email is not None and normalize_email(email) != user.email
            user.sqlmodel_update(changes)
            if email_changed:
                user.email_confirmed = False

            self._validate_user(user)
            self.session.add(user)
            await self.session.commit()
            return await self.load_user_company(user)
        except Exception as e:
            await self.session.rollback()
            raise e

    async def create_user(self, user: User, roles: Sequence[Role] = ()) -> User:
        try:
            self._validate_user(user)
            self.session.add(user)
            user.roles = list(roles)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update_keycloak_user(
        self, db_user: User, keycloak_user: User, roles: Sequence[Role]
    ) -> User:
        try:
            db_user.email = keycloak_user.email
            db_user.first_name = keycloak_user.first_name
            db_user.last_name = keycloak_user.last_name
            db_user.is_staff = keycloak_user.is_staff
            db_user.is_admin = keycloak_user.is_admin
            db_user.user_confirmed = keycloak_user.user_confirmed
            db_user.email_confirmed = keycloak_user.email_confirmed

            await self.load_user_roles(db_user)
            db_user.roles = list(roles)
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
            await self.update_where(
                User, col(User.id) == user_id, password=new_password_hash
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

    async def clear_pending_invite(self, user: User) -> None:
        try:
            user.pending_invite_token = None
            self.session.add(user)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
