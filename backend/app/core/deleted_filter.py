from collections.abc import Iterator
from threading import Lock

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria
from sqlalchemy.sql.base import Executable
from sqlmodel import SQLModel

from app.models.base import AppBase

INCLUDE_DELETED = "include_deleted"
_is_registered = False
_register_lock = Lock()


def include_deleted(statement: Executable) -> Executable:
    return statement.execution_options(**{INCLUDE_DELETED: True})


def _model_subclasses(model: type[SQLModel]) -> Iterator[type[SQLModel]]:
    for subclass in model.__subclasses__():
        yield subclass
        yield from _model_subclasses(subclass)


def _exclude_deleted_rows(execute_state: ORMExecuteState) -> None:
    """Exclude rows where deleted_at is not null from all ORM queries by default
    i.e. exclude deleted rows from query results"""
    if (
        not execute_state.is_select
        or execute_state.is_column_load
        or execute_state.is_relationship_load
        or execute_state.execution_options.get(INCLUDE_DELETED)
    ):
        return

    execute_state.statement = execute_state.statement.options(
        *(
            with_loader_criteria(
                model,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            )
            for model in _model_subclasses(AppBase)
            if hasattr(model, "deleted_at")
        )
    )


def register_deleted_filter() -> None:
    global _is_registered
    if _is_registered:
        return
    with _register_lock:
        if _is_registered:
            return
        event.listen(Session, "do_orm_execute", _exclude_deleted_rows)
        _is_registered = True
