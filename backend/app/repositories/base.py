from collections.abc import Sequence
from typing import Any, Generic, TypeVar, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, col, select

from app.models.base import BaseEntity

T = TypeVar("T", bound=SQLModel)
ModelT = TypeVar("ModelT", bound=SQLModel)


def rel(value: object) -> Any:
    return cast(Any, value)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def _get_by_field(self, field, value) -> T | None:
        statement = select(self.model).where(field == value)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    def _validate_model(
        self, instance: ModelT, *, exclude: set[str] | None = None
    ) -> ModelT:
        validated = instance.__class__.model_validate(
            instance.model_dump(exclude=exclude or set())
        )
        for field_name, value in validated.model_dump().items():
            setattr(instance, field_name, value)
        return instance

    async def get_by_id(self, entity_id: UUID) -> T | None:
        """Return one repository model row by id, or None if it does not exist."""
        if not issubclass(self.model, BaseEntity):
            raise TypeError(
                f"{self.model.__name__} does not inherit from BaseEntity and has no id field"
            )
        return await self._get_by_field(col(self.model.id), entity_id)

    async def lock_model_by_id(
        self, model: type[ModelT], entity_id: UUID
    ) -> ModelT | None:
        """Lock one model row until the current transaction commits or rolls back."""
        if not issubclass(model, BaseEntity):
            raise TypeError(
                f"{model.__name__} does not inherit from BaseEntity and has no id field"
            )
        statement = select(model).where(col(model.id) == entity_id).with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[UUID]) -> Sequence[T]:
        """Return repository model rows matching the given ids."""
        if not issubclass(self.model, BaseEntity):
            raise TypeError(
                f"{self.model.__name__} does not inherit from BaseEntity and has no id field"
            )
        statement = select(self.model).where(col(self.model.id).in_(ids))
        result = await self.session.execute(statement)
        return cast(Sequence[T], result.scalars().all())
