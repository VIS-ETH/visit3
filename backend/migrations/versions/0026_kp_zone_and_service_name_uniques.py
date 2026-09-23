"""Scope KP booth zone and service uniqueness to active rows

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: Union[str, Sequence[str], None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ZONE_TABLE = "kpeventboothzone"
ZONE_NAME_UQ = "kpeventboothzone_event_id_name_key"
ZONE_NAME_IX = "ix_kpeventboothzone_event_id_name"
ZONE_COLOR_UQ = "kpeventboothzone_event_id_color_key"
ZONE_COLOR_IX = "ix_kpeventboothzone_event_id_color"
SERVICE_TABLE = "kpeventservice"
SERVICE_NAME_UQ = "kpeventservice_event_id_name_key"
SERVICE_NAME_IX = "ix_kpeventservice_event_id_name"
NOT_DELETED = sa.text("deleted_at IS NULL")


def _drop_generated_unique(table_name: str, constraint_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}")


def upgrade() -> None:
    _drop_generated_unique(ZONE_TABLE, ZONE_NAME_UQ)
    op.create_index(
        ZONE_NAME_IX,
        ZONE_TABLE,
        ["event_id", "name"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )
    _drop_generated_unique(ZONE_TABLE, ZONE_COLOR_UQ)
    op.create_index(
        ZONE_COLOR_IX,
        ZONE_TABLE,
        ["event_id", "color"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )
    _drop_generated_unique(SERVICE_TABLE, SERVICE_NAME_UQ)
    op.create_index(
        SERVICE_NAME_IX,
        SERVICE_TABLE,
        ["event_id", "name"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )


def downgrade() -> None:
    op.drop_index(SERVICE_NAME_IX, table_name=SERVICE_TABLE)
    op.create_unique_constraint(SERVICE_NAME_UQ, SERVICE_TABLE, ["event_id", "name"])
    op.drop_index(ZONE_COLOR_IX, table_name=ZONE_TABLE)
    op.create_unique_constraint(ZONE_COLOR_UQ, ZONE_TABLE, ["event_id", "color"])
    op.drop_index(ZONE_NAME_IX, table_name=ZONE_TABLE)
    op.create_unique_constraint(ZONE_NAME_UQ, ZONE_TABLE, ["event_id", "name"])
