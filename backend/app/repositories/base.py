from typing import Generic, TypeVar

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def _get_by_field(self, field: ColumnElement, value) -> T | None:
        statement = select(self.model).where(field == value)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list) -> list[T]:
        statement = select(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(statement)
        return result.scalars().all()
