from typing import TypeVar, Generic
from sqlalchemy import ColumnElement
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=SQLModel)

class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def _get_by_field(self, field: ColumnElement, value) -> T | None:
        stmt = select(self.model).where(field == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
