from threading import Lock

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.models.base import AppBase

INCLUDE_DELETED = "include_deleted"
_is_registered = False
_register_lock = Lock()


def include_deleted(statement):
    return statement.execution_options(**{INCLUDE_DELETED: True})


def _exclude_deleted_rows(execute_state):
    if (
        not execute_state.is_select
        or execute_state.is_column_load
        or execute_state.is_relationship_load
        or execute_state.execution_options.get(INCLUDE_DELETED)
    ):
        return

    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            AppBase,
            lambda cls: cls.deleted_at.is_(None),
            include_aliases=True,
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
