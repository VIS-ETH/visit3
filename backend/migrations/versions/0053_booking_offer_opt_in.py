from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0053"
down_revision: Union[str, Sequence[str], None] = "0052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BOOKING_TABLE = "kpeventbooking"
OLD_ACTIVE_BOOKING = "status NOT IN ('CANCELLED', 'REJECTED') AND deleted_at IS NULL"
NEW_ACTIVE_BOOKING = (
    "status NOT IN ('CANCELLED', 'REJECTED', 'EXPIRED') AND deleted_at IS NULL"
)
ACTIVE_BOOKING_INDEXES = [
    (
        "ix_kpeventbooking_event_id_company_id_booth_zone_id",
        ["event_id", "company_id", "booth_zone_id"],
        "{active}",
    ),
    (
        "ix_kpeventbooking_event_id_booth_zone_id_booth_nr",
        ["event_id", "booth_zone_id", "booth_nr"],
        "booth_nr IS NOT NULL AND {active}",
    ),
]
OFFER_COLUMNS = (
    ("offer_made_on", sa.Date()),
    ("offer_week_reminder_sent_at", postgresql.TIMESTAMP(timezone=True)),
    ("offer_day_reminder_sent_at", postgresql.TIMESTAMP(timezone=True)),
)
ZURICH_TODAY = "(now() AT TIME ZONE 'Europe/Zurich')::date"
OFFERED_MAIL_TEMPLATE_DELETE = "DELETE FROM mailtemplate WHERE key = 'booking_offered'"

booking_status_with_offers = postgresql.ENUM(
    "OFFERED",
    "REGISTERED",
    "CONFIRMED",
    "CANCELLED",
    "REJECTED",
    "EXPIRED",
    name="kpbookingstatus_new",
)

booking_status_without_offers = postgresql.ENUM(
    "REGISTERED",
    "CONFIRMED",
    "CANCELLED",
    "REJECTED",
    name="kpbookingstatus_old",
)


def _swap_booking_status_enum(target: postgresql.ENUM, active: str) -> None:
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
            postgresql_where=sa.text(predicate.format(active=active)),
        )


def upgrade() -> None:
    _swap_booking_status_enum(booking_status_with_offers, NEW_ACTIVE_BOOKING)
    op.alter_column(
        BOOKING_TABLE, "offer_cancel_until", new_column_name="offer_deadline"
    )
    for column_name, column_type in OFFER_COLUMNS:
        op.add_column(BOOKING_TABLE, sa.Column(column_name, column_type, nullable=True))
    op.execute(
        f"""
        UPDATE {BOOKING_TABLE}
        SET status = 'OFFERED',
            offer_deadline = CASE
                WHEN offer_deadline < {ZURICH_TODAY} THEN {ZURICH_TODAY} + 7
                ELSE offer_deadline
            END,
            offer_made_on = {ZURICH_TODAY}
        WHERE offer_deadline IS NOT NULL
          AND status = 'REGISTERED'
          AND deleted_at IS NULL
        """
    )
    op.execute(OFFERED_MAIL_TEMPLATE_DELETE)


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE {BOOKING_TABLE}
        SET status = 'REGISTERED'
        WHERE status = 'OFFERED'
        """
    )
    op.execute(
        f"""
        UPDATE {BOOKING_TABLE}
        SET status = 'CANCELLED'
        WHERE status = 'EXPIRED'
        """
    )
    for column_name, _ in reversed(OFFER_COLUMNS):
        op.drop_column(BOOKING_TABLE, column_name)
    op.alter_column(
        BOOKING_TABLE, "offer_deadline", new_column_name="offer_cancel_until"
    )
    _swap_booking_status_enum(booking_status_without_offers, OLD_ACTIVE_BOOKING)
