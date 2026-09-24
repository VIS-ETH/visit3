from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037"
down_revision: Union[str, Sequence[str], None] = "0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BOOKING_TABLE = "kpeventbooking"
ACTIVE_BOOKING = "status NOT IN ('CANCELLED', 'REJECTED') AND deleted_at IS NULL"
ACTIVE_BOOKING_INDEXES = [
    (
        "ix_kpeventbooking_event_id_company_id_booth_zone_id",
        ["event_id", "company_id", "booth_zone_id"],
        ACTIVE_BOOKING,
    ),
    (
        "ix_kpeventbooking_event_id_booth_zone_id_booth_nr",
        ["event_id", "booth_zone_id", "booth_nr"],
        f"booth_nr IS NOT NULL AND {ACTIVE_BOOKING}",
    ),
]
FINALIZATION_COLUMNS = ("finalized_at", "auto_finalize_blocked_at")
FINALIZED_MAIL_TEMPLATE_DELETE = (
    "DELETE FROM mailtemplate WHERE key = 'booking_finalized'"
)

booking_status_without_finalized = postgresql.ENUM(
    "REGISTERED",
    "CONFIRMED",
    "CANCELLED",
    "REJECTED",
    name="kpbookingstatus_new",
)

booking_status_with_finalized = postgresql.ENUM(
    "REGISTERED",
    "FINALIZED",
    "CONFIRMED",
    "CANCELLED",
    "REJECTED",
    name="kpbookingstatus_old",
)


def _swap_booking_status_enum(target: postgresql.ENUM) -> None:
    target.create(op.get_bind(), checkfirst=True)
    for index_name, _, _ in ACTIVE_BOOKING_INDEXES:
        op.drop_index(index_name, table_name=BOOKING_TABLE)
    op.execute(
        f"""
        ALTER TABLE {BOOKING_TABLE}
        ALTER COLUMN status TYPE {target.name}
        USING status::text::{target.name}
        """
    )
    op.execute("DROP TYPE kpbookingstatus")
    op.execute(f"ALTER TYPE {target.name} RENAME TO kpbookingstatus")
    for index_name, columns, predicate in ACTIVE_BOOKING_INDEXES:
        op.create_index(
            index_name,
            BOOKING_TABLE,
            columns,
            unique=True,
            postgresql_where=sa.text(predicate),
        )


def upgrade() -> None:
    op.execute(
        f"UPDATE {BOOKING_TABLE} SET status = 'REGISTERED' WHERE status = 'FINALIZED'"
    )
    _swap_booking_status_enum(booking_status_without_finalized)
    for column_name in FINALIZATION_COLUMNS:
        op.drop_column(BOOKING_TABLE, column_name)
    op.execute(FINALIZED_MAIL_TEMPLATE_DELETE)


def downgrade() -> None:
    for column_name in FINALIZATION_COLUMNS:
        op.add_column(
            BOOKING_TABLE,
            sa.Column(column_name, postgresql.TIMESTAMP(timezone=True), nullable=True),
        )
    _swap_booking_status_enum(booking_status_with_finalized)
