"""KP booking rejection status and lifecycle timestamps

Revision ID: 0029
Revises: 0028
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import TextClause

revision: str = "0029"
down_revision: Union[str, Sequence[str], None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BOOKING_TABLE = "kpeventbooking"
BOOKING_ZONE_IX = "ix_kpeventbooking_event_id_company_id_booth_zone_id"
BOOKING_ZONE_COLUMNS = ["event_id", "company_id", "booth_zone_id"]
BOOTH_NR_IX = "ix_kpeventbooking_event_id_booth_zone_id_booth_nr"
BOOTH_NR_COLUMNS = ["event_id", "booth_zone_id", "booth_nr"]

WITHOUT_REJECTED = "status <> 'CANCELLED' AND deleted_at IS NULL"
WITH_REJECTED = "status NOT IN ('CANCELLED', 'REJECTED') AND deleted_at IS NULL"

TIMESTAMP_COLUMNS = (
    "status_changed_at",
    "finalized_at",
    "confirmed_at",
    "auto_finalize_blocked_at",
)
TEXT_COLUMNS = ("status_note", "rejection_reason")

booking_status_with_rejected = postgresql.ENUM(
    "REGISTERED",
    "FINALIZED",
    "CONFIRMED",
    "CANCELLED",
    "REJECTED",
    name="kpbookingstatus_new",
)

booking_status_without_rejected = postgresql.ENUM(
    "REGISTERED",
    "FINALIZED",
    "CONFIRMED",
    "CANCELLED",
    name="kpbookingstatus_old",
)


def _swap_booking_status_enum(target: postgresql.ENUM) -> None:
    target.create(op.get_bind(), checkfirst=True)
    op.execute(
        f"""
        ALTER TABLE {BOOKING_TABLE}
        ALTER COLUMN status TYPE {target.name}
        USING status::text::{target.name}
        """
    )
    op.execute("DROP TYPE kpbookingstatus")
    op.execute(f"ALTER TYPE {target.name} RENAME TO kpbookingstatus")


def _active_booking_indexes(active: str) -> None:
    booking_predicate: TextClause = sa.text(active)
    numbered_predicate: TextClause = sa.text(f"booth_nr IS NOT NULL AND {active}")
    op.drop_index(BOOKING_ZONE_IX, table_name=BOOKING_TABLE)
    op.create_index(
        BOOKING_ZONE_IX,
        BOOKING_TABLE,
        BOOKING_ZONE_COLUMNS,
        unique=True,
        postgresql_where=booking_predicate,
    )
    op.drop_index(BOOTH_NR_IX, table_name=BOOKING_TABLE)
    op.create_index(
        BOOTH_NR_IX,
        BOOKING_TABLE,
        BOOTH_NR_COLUMNS,
        unique=True,
        postgresql_where=numbered_predicate,
    )


def upgrade() -> None:
    for column_name in TIMESTAMP_COLUMNS:
        op.add_column(
            BOOKING_TABLE,
            sa.Column(column_name, sa.TIMESTAMP(timezone=True), nullable=True),
        )
    for column_name in TEXT_COLUMNS:
        op.add_column(BOOKING_TABLE, sa.Column(column_name, sa.String(), nullable=True))
    _swap_booking_status_enum(booking_status_with_rejected)
    _active_booking_indexes(WITH_REJECTED)


def downgrade() -> None:
    op.execute(
        f"UPDATE {BOOKING_TABLE} SET status = 'CANCELLED' WHERE status = 'REJECTED'"
    )
    _active_booking_indexes(WITHOUT_REJECTED)
    _swap_booking_status_enum(booking_status_without_rejected)
    for column_name in reversed(TEXT_COLUMNS):
        op.drop_column(BOOKING_TABLE, column_name)
    for column_name in reversed(TIMESTAMP_COLUMNS):
        op.drop_column(BOOKING_TABLE, column_name)
