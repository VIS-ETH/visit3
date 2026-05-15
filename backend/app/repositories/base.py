from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql._typing import ColumnExpressionArgument
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import SQLModel, col, select, update
from sqlmodel import delete as sql_delete

from app.models.base import AppBase, BaseEntity

T = TypeVar("T", bound=SQLModel)
ModelT = TypeVar("ModelT", bound=SQLModel)


def rel(value: object) -> Any:
    return cast(Any, value)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def _get_by_field(
        self, field: ColumnExpressionArgument[Any], value: object
    ) -> T | None:
        statement = select(self.model).where(field == value)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    def _not_deleted(self, model: type[AppBase]) -> ColumnElement[bool]:
        """Return the condition used to target rows that are not deleted."""
        return col(model.deleted_at).is_(None)

    def _validate_model(
        self, instance: ModelT, *, exclude: set[str] | None = None
    ) -> ModelT:
        validated = instance.__class__.model_validate(
            instance.model_dump(exclude=exclude or set())
        )
        for field_name, value in validated.model_dump().items():
            setattr(instance, field_name, value)
        return instance

    async def load_fields(self, instance: ModelT, *fields: str) -> ModelT:
        """Load selected fields or relationships on an instance."""
        await self.session.refresh(instance, attribute_names=list(fields))
        return instance

    async def get_by_id(self, entity_id: UUID) -> T | None:
        """Return one active repository model row by id, or None."""
        if not issubclass(self.model, BaseEntity):
            raise TypeError(
                f"{self.model.__name__} does not inherit from BaseEntity and has no id field"
            )
        statement = select(self.model).where(col(self.model.id) == entity_id)
        result = await self.session.execute(statement)
        return cast(T | None, result.scalar_one_or_none())

    async def lock_model_by_id(
        self, model: type[ModelT], entity_id: UUID
    ) -> ModelT | None:
        """Lock one active model row until the transaction ends."""
        if not issubclass(model, BaseEntity):
            raise TypeError(
                f"{model.__name__} does not inherit from BaseEntity and has no id field"
            )
        statement = select(model).where(col(model.id) == entity_id).with_for_update()
        result = await self.session.execute(statement)
        return cast(ModelT | None, result.scalar_one_or_none())

    async def get_by_ids(self, ids: list[UUID]) -> Sequence[T]:
        """Return active repository model rows matching the given ids."""
        if not issubclass(self.model, BaseEntity):
            raise TypeError(
                f"{self.model.__name__} does not inherit from BaseEntity and has no id field"
            )
        statement = select(self.model).where(col(self.model.id).in_(ids))
        result = await self.session.execute(statement)
        return cast(Sequence[T], result.scalars().all())

    def delete(self, instance: AppBase) -> None:
        """Mark one model row as deleted."""
        instance.mark_deleted()
        self.session.add(instance)

    async def hard_delete(self, instance: SQLModel) -> None:
        """Permanently delete one model row."""
        await self.session.delete(instance)

    async def delete_where(
        self, model: type[AppBase], *conditions: ColumnElement[bool]
    ) -> None:
        """Mark model rows matching the conditions as deleted."""
        statement = (
            update(model)
            .where(self._not_deleted(model), *conditions)
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await self.session.execute(statement)

    async def hard_delete_where(
        self, model: type[SQLModel], *conditions: ColumnElement[bool]
    ) -> None:
        """Permanently delete model rows matching the conditions."""
        statement = sql_delete(model).where(*conditions)
        await self.session.execute(statement)
