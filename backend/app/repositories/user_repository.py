import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql._typing import ColumnExpressionArgument
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select
from sqlmodel import col, or_, select

from app.core.dates import utc_now
from app.core.exceptions import EmailTakenLocally, EmailUsed
from app.core.utils import normalize_email
from app.models.company import Company, KpCompanyProfile
from app.models.user import Role, User
from app.repositories.base import BaseRepository, ordered, rel
from app.schemas.sorting import SortDirection
from app.schemas.user import UserFilter, UserProfileFieldsInput, UserSort


def _filter_conditions(
    user_filter: UserFilter, since: datetime | None
) -> list[ColumnElement[bool]]:
    if user_filter is UserFilter.NEW and since is not None:
        return [
            or_(col(User.created_at) > since, col(User.new_in_company_since) > since)
        ]
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


def _sort_expressions(sort: UserSort) -> list[ColumnExpressionArgument[Any]]:
    match sort:
        case UserSort.EMAIL:
            return [col(User.email)]
        case UserSort.NAME:
            return [
                func.lower(func.coalesce(col(User.first_name), "")),
                func.lower(func.coalesce(col(User.last_name), "")),
            ]
        case UserSort.COMPANY:
            return [func.lower(col(Company.name))]
        case UserSort.ROLE:
            return [col(User.is_admin), col(User.is_staff), col(User.is_company)]
        case UserSort.STATUS:
            return [col(User.email_confirmed)]
        case UserSort.SIGNED_UP:
            return [col(User.created_at)]
        case UserSort.LAST_LOGIN:
            return [col(User.last_login_at)]


def _user_order(
    sort: UserSort | None, direction: SortDirection
) -> list[ColumnExpressionArgument[Any]]:
    if sort is None:
        return [col(User.email), col(User.id)]
    return [
        *ordered(_sort_expressions(sort), direction),
        col(User.email),
        col(User.id),
    ]


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

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
        self,
        query: str | None,
        user_filter: UserFilter,
        since: datetime | None,
        company_id: uuid.UUID | None = None,
    ) -> Select[tuple[User]]:
        return (
            select(User)
            .outerjoin(
                Company,
                (col(User.company_id) == col(Company.id)) & self._not_deleted(Company),
            )
            .where(
                self._not_deleted(User),
                *_filter_conditions(user_filter, since),
                *_search_conditions(query),
                *([col(User.company_id) == company_id] if company_id else []),
            )
        )

    async def count_users_matching(
        self,
        query: str | None,
        user_filter: UserFilter,
        since: datetime | None = None,
        company_id: uuid.UUID | None = None,
    ) -> int:
        statement = self._searchable_users(
            query, user_filter, since, company_id
        ).with_only_columns(func.count(col(User.id)))
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def search_users(
        self,
        query: str | None,
        user_filter: UserFilter,
        offset: int,
        limit: int,
        sort: UserSort | None = None,
        direction: SortDirection = SortDirection.ASC,
        since: datetime | None = None,
        company_id: uuid.UUID | None = None,
    ) -> Sequence[User]:
        statement = (
            self._searchable_users(query, user_filter, since, company_id)
            .options(selectinload(rel(User.company)))
            .execution_options(populate_existing=True)
            .order_by(*_user_order(sort, direction))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def purge_unconfirmed_accounts(self, max_age: timedelta) -> int:
        cutoff = utc_now() - max_age
        statement = select(User).where(
            col(User.email_confirmed) == False,
            col(User.company_id).is_(None),
            col(User.sub).is_(None),
            col(User.is_staff).is_(False),
            col(User.is_admin).is_(False),
            col(User.created_at) < cutoff,
        )
        stale = (await self.session.execute(statement)).scalars().all()
        for user in stale:
            await self.delete_user(user)
        return len(stale)

    async def delete_user(self, user: User):
        async with self.committing():
            await self.update_where(
                KpCompanyProfile,
                col(KpCompanyProfile.kp_contact_user_id) == user.id,
                kp_contact_user_id=None,
            )
            self.delete(user)

    async def update_user(self, user: User, update: UserProfileFieldsInput) -> User:
        async with self.committing():
            changes = update.model_dump(exclude_unset=True)
            if "company_id" in changes and changes["company_id"] != user.company_id:
                changes["new_in_company_since"] = (
                    utc_now() if changes["company_id"] is not None else None
                )
                await self.update_where(
                    KpCompanyProfile,
                    col(KpCompanyProfile.kp_contact_user_id) == user.id,
                    kp_contact_user_id=None,
                )
            email = changes.get("email")
            email_changed = email is not None and normalize_email(email) != user.email
            user.sqlmodel_update(changes)
            if email_changed:
                user.email_confirmed = False

            self._validate_model(user)
            self.session.add(user)
        return await self.load_user_company(user)

    async def create_user(self, user: User, roles: Sequence[Role] = ()) -> User:
        try:
            async with self.committing():
                self._validate_model(user)
                self.session.add(user)
                user.roles = list(roles)
        except IntegrityError:
            raise EmailUsed(f"create_user:{user.email}") from None
        await self.session.refresh(user)
        return user

    async def update_keycloak_user(
        self, db_user: User, keycloak_user: User, roles: Sequence[Role]
    ) -> User:
        user_id = db_user.id
        try:
            async with self.committing():
                db_user.email = keycloak_user.email
                db_user.first_name = keycloak_user.first_name
                db_user.last_name = keycloak_user.last_name
                db_user.is_staff = keycloak_user.is_staff
                db_user.is_admin = keycloak_user.is_admin
                db_user.email_confirmed = keycloak_user.email_confirmed

                await self.load_user_roles(db_user)
                db_user.roles = list(roles)
                self._validate_model(db_user)
                self.session.add(db_user)
        except IntegrityError:
            raise EmailTakenLocally(f"keycloak_update:{user_id}") from None
        await self.session.refresh(db_user)
        return db_user

    async def revoke_privileges(self, user: User) -> None:
        async with self.committing():
            await self.load_user_roles(user)
            user.is_staff = False
            user.is_admin = False
            user.roles = []
            self.session.add(user)

    async def update_password(
        self, user_id: uuid.UUID, new_password_hash: str, confirm_email: bool = False
    ):
        async with self.committing():
            values: dict[str, Any] = {"password": new_password_hash}
            if confirm_email:
                values["email_confirmed"] = True
            await self.update_where(User, col(User.id) == user_id, **values)

    async def record_login(self, user_id: uuid.UUID) -> None:
        async with self.committing():
            await self.update_where(
                User,
                col(User.id) == user_id,
                previous_login_at=col(User.last_login_at),
                last_login_at=utc_now(),
            )

    async def confirm_email(self, user: User):
        async with self.committing():
            user.email_confirmed = True
            self.session.add(user)

    async def set_pending_email(self, user: User, email: str | None) -> User:
        async with self.committing():
            user.pending_email = email
            self.session.add(user)
        return await self.load_user_company(user)

    async def apply_email_change(self, user: User, email: str) -> User:
        try:
            async with self.committing():
                user.email = email
                user.email_confirmed = True
                user.pending_email = None
                self._validate_model(user)
                self.session.add(user)
        except IntegrityError:
            raise EmailUsed(f"apply_email_change:{email}") from None
        return user

    async def clear_pending_invite(self, user: User) -> None:
        async with self.committing():
            user.pending_invite_token = None
            self.session.add(user)
