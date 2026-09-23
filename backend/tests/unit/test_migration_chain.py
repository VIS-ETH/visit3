import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Column, Constraint, Index, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.schema import MetaData
from sqlmodel import SQLModel

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DELETES_ALLOWED_IN_UPGRADES: dict[str, str] = {}
FORBIDDEN_RAW_DDL = (
    "CREATE TABLE",
    "DROP TABLE",
    "ADD COLUMN",
    "DROP COLUMN",
    "RENAME COLUMN",
)

Schema = dict[str, set[str]]


class EmptyResult:
    def scalars(self) -> "EmptyResult":
        return self

    def all(self) -> list[Any]:
        return []


class RecordingBind:
    dialect = postgresql.dialect()

    def __init__(self) -> None:
        self.queries: list[str] = []

    def execute(self, statement: object, *args: Any, **kwargs: Any) -> EmptyResult:
        self.queries.append(str(statement))
        return EmptyResult()

    def _run_ddl_visitor(self, *args: Any, **kwargs: Any) -> None:
        return None


def is_generated_constraint_name(constraint_name: str, table_name: str) -> bool:
    return constraint_name.startswith(f"{table_name}_") and constraint_name.endswith(
        "_key"
    )


class SchemaRecorder:
    def __init__(self) -> None:
        self.tables: Schema = {}
        self.named_objects: set[tuple[str, str]] = set()
        self.statements: list[str] = []
        self.server_defaults: set[tuple[str, str]] = set()
        self.bind = RecordingBind()
        self.upgrading = True

    def snapshot(self) -> Schema:
        return {table: set(columns) for table, columns in self.tables.items()}

    def f(self, name: str) -> str:
        return name

    def get_bind(self) -> RecordingBind:
        return self.bind

    def execute(self, statement: object, *args: Any, **kwargs: Any) -> None:
        if self.upgrading:
            self.statements.append(str(statement))
        sql = str(statement).upper()
        hidden = [keyword for keyword in FORBIDDEN_RAW_DDL if keyword in sql]
        assert not hidden, f"raw SQL hides schema changes from this test: {hidden}"
        assert "DROP CONSTRAINT" not in sql or "DROP CONSTRAINT IF EXISTS" in sql, (
            f"raw constraint drop must tolerate a missing constraint: {sql}"
        )

    def _track_server_default(self, table_name: str, column: Column[Any]) -> None:
        entry = (table_name, str(column.name))
        if column.server_default is None:
            self.server_defaults.discard(entry)
        else:
            self.server_defaults.add(entry)

    def create_table(self, table_name: str, *elements: object, **kwargs: Any) -> None:
        assert table_name not in self.tables, f"{table_name} already exists"
        columns: set[str] = set()
        for element in elements:
            if isinstance(element, Column):
                columns.add(str(element.name))
                self._track_server_default(table_name, element)
            elif isinstance(element, (Constraint, Index)) and isinstance(
                element.name, str
            ):
                self.named_objects.add((table_name, element.name))
        self.tables[table_name] = columns

    def drop_table(self, table_name: str, **kwargs: Any) -> None:
        assert table_name in self.tables, f"{table_name} does not exist"
        del self.tables[table_name]
        self.named_objects = {
            entry for entry in self.named_objects if entry[0] != table_name
        }
        self.server_defaults = {
            entry for entry in self.server_defaults if entry[0] != table_name
        }

    def add_column(self, table_name: str, column: Column[Any], **kwargs: Any) -> None:
        self.tables[table_name].add(str(column.name))
        self._track_server_default(table_name, column)

    def drop_column(self, table_name: str, column_name: str, **kwargs: Any) -> None:
        assert column_name in self.tables[table_name], (
            f"{table_name}.{column_name} does not exist"
        )
        self.tables[table_name].remove(column_name)
        self.server_defaults.discard((table_name, column_name))

    def alter_column(self, table_name: str, column_name: str, **kwargs: Any) -> None:
        if "server_default" in kwargs:
            entry = (table_name, column_name)
            if kwargs["server_default"] is None:
                self.server_defaults.discard(entry)
            else:
                self.server_defaults.add(entry)
        new_column_name = kwargs.get("new_column_name")
        if new_column_name is None:
            return
        self.tables[table_name].remove(column_name)
        self.tables[table_name].add(new_column_name)
        self.server_defaults.discard((table_name, column_name))

    def create_index(
        self, index_name: str, table_name: str, columns: object, **kwargs: Any
    ) -> None:
        self.named_objects.add((table_name, index_name))

    def drop_index(
        self, index_name: str, table_name: str | None = None, **kwargs: Any
    ) -> None:
        self.named_objects.discard((str(table_name), index_name))

    def create_unique_constraint(
        self, constraint_name: str, table_name: str, columns: object, **kwargs: Any
    ) -> None:
        self.named_objects.add((table_name, constraint_name))

    def create_check_constraint(
        self, constraint_name: str, table_name: str, condition: object, **kwargs: Any
    ) -> None:
        self.named_objects.add((table_name, constraint_name))

    def create_foreign_key(
        self,
        constraint_name: str | None,
        source_table: str,
        referent_table: str,
        local_cols: object,
        remote_cols: object,
        **kwargs: Any,
    ) -> None:
        if constraint_name is not None:
            self.named_objects.add((source_table, constraint_name))

    def drop_constraint(
        self, constraint_name: str, table_name: str, **kwargs: Any
    ) -> None:
        assert not (
            self.upgrading
            and kwargs.get("type_") == "unique"
            and is_generated_constraint_name(constraint_name, table_name)
        ), (
            f"{constraint_name} is named by postgres and may be missing; "
            "drop it with raw SQL using IF EXISTS"
        )
        self.named_objects.discard((table_name, constraint_name))

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"migration uses an unsupported operation: op.{name}")


def versions_directory() -> Path:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    return Path(ScriptDirectory.from_config(config).versions)


def load_migrations() -> list[ModuleType]:
    modules: list[ModuleType] = []
    for path in sorted(versions_directory().glob("*.py")):
        spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return sorted(modules, key=lambda module: module.revision)


def replay_upgrades(migrations: list[ModuleType]) -> SchemaRecorder:
    recorder = SchemaRecorder()
    for module in migrations:
        module.op = recorder
        module.upgrade()
    return recorder


def header_value(doc: str, label: str) -> str:
    prefix = f"{label}:"
    for line in doc.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def named_objects(table: Table) -> set[str]:
    names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint.name, str)
    }
    names |= {index.name for index in table.indexes if isinstance(index.name, str)}
    return names


@pytest.fixture(scope="module")
def migrations() -> list[ModuleType]:
    return load_migrations()


def test_revision_ids_match_file_names_and_headers(migrations: list[ModuleType]):
    for module in migrations:
        path = Path(str(module.__file__))
        assert path.stem.split("_", 1)[0] == module.revision
        doc = module.__doc__ or ""
        assert header_value(doc, "Revision ID") == module.revision
        assert header_value(doc, "Revises") == (module.down_revision or "")


def test_revision_chain_is_linear_with_a_single_head(migrations: list[ModuleType]):
    revisions = [module.revision for module in migrations]
    assert len(set(revisions)) == len(revisions)
    assert all(
        isinstance(revision, str) and revision.isdigit() and len(revision) == 4
        for revision in revisions
    )
    roots = [module for module in migrations if module.down_revision is None]
    assert len(roots) == 1
    for module in migrations:
        if module.down_revision is None:
            continue
        assert module.down_revision == f"{int(module.revision) - 1:04d}"


def metadata_with_every_model_registered() -> MetaData:
    importlib.import_module("app.models")
    return SQLModel.metadata


def test_migrated_tables_and_columns_match_the_models(migrations: list[ModuleType]):
    recorder = replay_upgrades(migrations)
    expected = {
        name: set(table.columns.keys())
        for name, table in metadata_with_every_model_registered().tables.items()
    }
    assert recorder.tables == expected


def test_model_constraints_and_indexes_are_created_by_migrations(
    migrations: list[ModuleType],
):
    recorder = replay_upgrades(migrations)
    expected = {
        (table.name, name)
        for table in metadata_with_every_model_registered().tables.values()
        for name in named_objects(table)
    }
    assert expected, "no named constraints or indexes found in the models"
    assert expected <= recorder.named_objects


def test_every_downgrade_restores_the_previous_schema(migrations: list[ModuleType]):
    recorder = SchemaRecorder()
    snapshots: list[Schema] = []
    for module in migrations:
        module.op = recorder
        snapshots.append(recorder.snapshot())
        module.upgrade()

    recorder.upgrading = False
    for module, snapshot in zip(reversed(migrations), reversed(snapshots)):
        module.downgrade()
        assert recorder.snapshot() == snapshot, (
            f"downgrade of {module.revision} does not restore the previous schema"
        )

    assert recorder.tables == {}


def test_pre_check_queries_ignore_deleted_rows(migrations: list[ModuleType]):
    recorder = replay_upgrades(migrations)
    queries = [
        query
        for query in recorder.bind.queries
        if query.lstrip().upper().startswith("SELECT")
    ]
    assert queries, "no migration pre-check queries found"
    for query in queries:
        assert "deleted_at IS NULL" in query, (
            f"migration pre-check must ignore deleted rows: {query}"
        )


def test_mail_templates_are_never_seeded(migrations: list[ModuleType]):
    recorder = replay_upgrades(migrations)
    seeding = [
        statement
        for statement in recorder.statements
        if "INSERT INTO mailtemplate" in statement
    ]
    assert not seeding, "seeded rows would mark every mail template as customized"


def test_upgrades_never_delete_rows_without_a_reason(migrations: list[ModuleType]):
    recorder = replay_upgrades(migrations)
    deletions = [
        statement
        for statement in recorder.statements
        if "DELETE FROM" in statement.upper()
        and statement not in DELETES_ALLOWED_IN_UPGRADES
    ]
    assert not deletions, f"an upgrade that deletes rows needs a reason: {deletions}"


def test_server_defaults_match_the_models(migrations: list[ModuleType]):
    recorder = replay_upgrades(migrations)
    expected = {
        (name, column.name)
        for name, table in metadata_with_every_model_registered().tables.items()
        for column in table.columns
        if column.server_default is not None
    }
    assert recorder.server_defaults == expected
