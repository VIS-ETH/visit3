"""Scope KP uniqueness to active rows

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: Union[str, Sequence[str], None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BOOKING_TABLE = "kpeventbooking"
BOOKING_ZONE_UQ = "kpeventbooking_event_id_company_id_booth_zone_id_key"
BOOKING_ZONE_IX = "ix_kpeventbooking_event_id_company_id_booth_zone_id"
BOOTH_NR_UQ = "kpeventbooking_event_id_booth_zone_id_booth_nr_key"
BOOTH_NR_IX = "ix_kpeventbooking_event_id_booth_zone_id_booth_nr"
ACTIVE_BOOKING = sa.text("status <> 'CANCELLED' AND deleted_at IS NULL")
NUMBERED_ACTIVE_BOOKING = sa.text(
    "booth_nr IS NOT NULL AND status <> 'CANCELLED' AND deleted_at IS NULL"
)
BACKGROUND_TABLE = "kpeventnametagbackground"
BACKGROUND_IX = "ix_kpeventnametagbackground_event_id"
NOT_DELETED = sa.text("deleted_at IS NULL")
DEDUPLICATE_BACKGROUNDS = """
    UPDATE kpeventnametagbackground AS outdated
    SET deleted_at = now()
    WHERE outdated.deleted_at IS NULL
      AND EXISTS (
          SELECT 1
          FROM kpeventnametagbackground AS newest
          WHERE newest.event_id = outdated.event_id
            AND newest.deleted_at IS NULL
            AND (newest.updated_at, newest.id) > (outdated.updated_at, outdated.id)
      )
"""


def _drop_generated_unique(table_name: str, constraint_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}")


def upgrade() -> None:
    _drop_generated_unique(BOOKING_TABLE, BOOKING_ZONE_UQ)
    op.create_index(
        BOOKING_ZONE_IX,
        BOOKING_TABLE,
        ["event_id", "company_id", "booth_zone_id"],
        unique=True,
        postgresql_where=ACTIVE_BOOKING,
    )
    _drop_generated_unique(BOOKING_TABLE, BOOTH_NR_UQ)
    op.create_index(
        BOOTH_NR_IX,
        BOOKING_TABLE,
        ["event_id", "booth_zone_id", "booth_nr"],
        unique=True,
        postgresql_where=NUMBERED_ACTIVE_BOOKING,
    )
    op.execute(DEDUPLICATE_BACKGROUNDS)
    op.create_index(
        BACKGROUND_IX,
        BACKGROUND_TABLE,
        ["event_id"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )


def downgrade() -> None:
    op.drop_index(BACKGROUND_IX, table_name=BACKGROUND_TABLE)
    op.drop_index(BOOTH_NR_IX, table_name=BOOKING_TABLE)
    op.create_unique_constraint(
        BOOTH_NR_UQ,
        BOOKING_TABLE,
        ["event_id", "booth_zone_id", "booth_nr"],
    )
    op.drop_index(BOOKING_ZONE_IX, table_name=BOOKING_TABLE)
    op.create_unique_constraint(
        BOOKING_ZONE_UQ,
        BOOKING_TABLE,
        ["event_id", "company_id", "booth_zone_id"],
    )
