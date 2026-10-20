from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select
from sqlmodel import col, or_, select

from app.models.company import Company
from app.models.kp_event import KpEventBooking, KpEventBookingService
from app.models.user import User
from app.repositories.base import BaseRepository, rel


def booking_changed_since(since: datetime) -> ColumnElement[bool]:
    return or_(
        col(KpEventBooking.updated_at) > since,
        exists().where(
            col(KpEventBookingService.booking_id) == col(KpEventBooking.id),
            col(KpEventBookingService.updated_at) > since,
        ),
    )


def company_changed_since(since: datetime) -> ColumnElement[bool]:
    return or_(
        col(Company.created_at) > since,
        col(Company.id).in_(
            select(User.company_id).where(
                col(User.deleted_at).is_(None),
                col(User.new_in_company_since) > since,
            )
        ),
    )


class ChangeRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def _count(self, statement: Select[Any]) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(statement.subquery())
        )
        return result.scalar_one()

    async def new_users(
        self, since: datetime, limit: int
    ) -> tuple[Sequence[User], int]:
        statement = select(User).where(
            self._not_deleted(User), col(User.created_at) > since
        )
        result = await self.session.execute(
            statement.options(selectinload(rel(User.company)))
            .order_by(col(User.created_at).desc())
            .limit(limit)
        )
        return result.scalars().all(), await self._count(statement)

    async def new_companies(
        self, since: datetime, limit: int
    ) -> tuple[Sequence[Company], int]:
        statement = select(Company).where(
            self._not_deleted(Company), col(Company.created_at) > since
        )
        result = await self.session.execute(
            statement.order_by(col(Company.created_at).desc()).limit(limit)
        )
        return result.scalars().all(), await self._count(statement)

    async def bookings(
        self, since: datetime, limit: int, *, new: bool
    ) -> tuple[Sequence[KpEventBooking], int]:
        condition = (
            col(KpEventBooking.created_at) > since
            if new
            else (col(KpEventBooking.created_at) <= since)
            & booking_changed_since(since)
        )
        statement = select(KpEventBooking).where(
            self._not_deleted(KpEventBooking), condition
        )
        order = (
            col(KpEventBooking.created_at) if new else col(KpEventBooking.updated_at)
        )
        result = await self.session.execute(
            statement.options(
                selectinload(rel(KpEventBooking.event)),
                selectinload(rel(KpEventBooking.company)),
                selectinload(rel(KpEventBooking.booth_zone)),
                selectinload(rel(KpEventBooking.services)),
            )
            .order_by(order.desc())
            .limit(limit)
        )
        return result.scalars().all(), await self._count(statement)

    async def mark_changes_seen(self, user_id: UUID, seen_at: datetime) -> None:
        try:
            await self.update_where(
                User, col(User.id) == user_id, changes_seen_at=seen_at
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
