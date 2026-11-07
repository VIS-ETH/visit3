from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from typing import Any, Generic, TypeVar, cast
from uuid import UUID

from sqlalchemy import asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql._typing import ColumnExpressionArgument
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression
from sqlmodel import SQLModel, col, select, update
from sqlmodel import delete as sql_delete

from app.core.dates import utc_now
from app.models.base import AppBase, BaseEntity
from app.schemas.sorting import SortDirection

T = TypeVar("T", bound=SQLModel)
ModelT = TypeVar("ModelT", bound=SQLModel)


def rel(value: object) -> Any:
    return cast(Any, value)


def ordered(
    expressions: Sequence[ColumnExpressionArgument[Any]], direction: SortDirection
) -> list[UnaryExpression[Any]]:
    order = desc if direction is SortDirection.DESC else asc
    return [order(expression).nulls_last() for expression in expressions]


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    @asynccontextmanager
    async def committing(self) -> AsyncGenerator[None]:
        try:
            yield
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def end_read_transaction(self) -> None:
        if self.session.in_transaction():
            await self.session.commit()

    async def _get_by_field(
        self, field: ColumnExpressionArgument[Any], value: object
    ) -> T | None:
        statement = select(self.model).where(field == value)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    def _not_deleted(self, model: type[AppBase]) -> ColumnElement[bool]:
        return col(model.deleted_at).is_(None)

    def _validate_model(self, instance: ModelT) -> ModelT:
        validated = instance.__class__.model_validate(instance.model_dump())
        for field_name, value in validated.model_dump().items():
            setattr(instance, field_name, value)
        return instance

    def _clone_model(
        self,
        model: type[ModelT],
        source: SQLModel,
        fields: Sequence[str],
        **overrides: Any,
    ) -> ModelT:
        values = source.model_dump(include=set(fields))
        values.update(overrides)
        cloned = model(**values)
        self.session.add(cloned)
        return cloned

    async def get_by_id(self, entity_id: UUID) -> T | None:
        if not issubclass(self.model, BaseEntity):
            raise TypeError(
                f"{self.model.__name__} does not inherit from BaseEntity and has no id field"
            )
        statement = select(self.model).where(col(self.model.id) == entity_id)
        result = await self.session.execute(statement)
        return cast(T | None, result.scalar_one_or_none())

    async def release_locks(self) -> None:
        await self.session.commit()

    async def lock_model_by_id(
        self, model: type[ModelT], entity_id: UUID
    ) -> ModelT | None:
        if not issubclass(model, BaseEntity):
            raise TypeError(
                f"{model.__name__} does not inherit from BaseEntity and has no id field"
            )
        statement = (
            select(model)
            .where(col(model.id) == entity_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return cast(ModelT | None, result.scalar_one_or_none())

    def delete(self, instance: AppBase) -> None:
        instance.mark_deleted()
        self.session.add(instance)

    async def hard_delete(self, instance: SQLModel) -> None:
        await self.session.delete(instance)

    async def update_where(
        self,
        model: type[AppBase],
        *conditions: ColumnElement[bool],
        **values: Any,
    ) -> None:
        statement = (
            update(model).where(self._not_deleted(model), *conditions).values(**values)
        )
        await self.session.execute(statement)

    async def delete_where(
        self, model: type[AppBase], *conditions: ColumnElement[bool]
    ) -> None:
        await self.update_where(model, *conditions, deleted_at=utc_now())

    async def hard_delete_where(
        self, model: type[SQLModel], *conditions: ColumnElement[bool]
    ) -> None:
        statement = sql_delete(model).where(*conditions)
        await self.session.execute(statement)
