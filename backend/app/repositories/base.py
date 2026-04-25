from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

from app.models.base import BaseEntity

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def _get_by_field(self, field: ColumnElement, value) -> T | None:
        statement = select(self.model).where(field == value)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, entity_id: UUID) -> T | None:
        if not issubclass(self.model, BaseEntity):
            raise TypeError(
                f"{self.model.__name__} does not inherit from BaseEntity and has no id field"
            )
        return await self._get_by_field(self.model.id, entity_id)

    async def get_by_ids(self, ids: list[UUID]) -> list[T]:
        if not issubclass(self.model, BaseEntity):
            raise TypeError(
                f"{self.model.__name__} does not inherit from BaseEntity and has no id field"
            )
        statement = select(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(statement)
        return result.scalars().all()
