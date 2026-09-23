"""KP event date checks and removal of the draft booking status

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: Union[str, Sequence[str], None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EVENT_TABLE = "kpevent"
EVENT_DATE_CHECKS = [
    ("kpevent_registration_open_before_end", "registration_open < registration_end"),
    ("kpevent_registration_end_before_event_date", "registration_end < event_date"),
    (
        "kpevent_finalization_on_or_after_registration_end",
        "finalization_deadline >= registration_end",
    ),
    ("kpevent_finalization_before_event_date", "finalization_deadline < event_date"),
    (
        "kpevent_nametags_on_or_after_registration_end",
        "nametags_deadline >= registration_end",
    ),
    ("kpevent_nametags_before_event_date", "nametags_deadline < event_date"),
]

BOOKING_TABLE = "kpeventbooking"

booking_status_without_draft = postgresql.ENUM(
    "REGISTERED",
    "FINALIZED",
    "CONFIRMED",
    "CANCELLED",
    name="kpbookingstatus_new",
)

booking_status_with_draft = postgresql.ENUM(
    "DRAFT",
    "REGISTERED",
    "FINALIZED",
    "CONFIRMED",
    "CANCELLED",
    name="kpbookingstatus_old",
)


def _reject_violating_events() -> None:
    bind = op.get_bind()
    violations: list[str] = []
    for name, condition in EVENT_DATE_CHECKS:
        event_ids = (
            bind.execute(
                sa.text(
                    f"SELECT id FROM {EVENT_TABLE} "
                    f"WHERE deleted_at IS NULL AND NOT ({condition}) "
                    "ORDER BY id"
                )
            )
            .scalars()
            .all()
        )
        if event_ids:
            listed = ", ".join(str(event_id) for event_id in event_ids)
            violations.append(f"{name} [{condition}]: {listed}")
    if violations:
        raise RuntimeError(
            "cannot add kpevent date check constraints, offending event ids -> "
            + " | ".join(violations)
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


def upgrade() -> None:
    _reject_violating_events()
    for name, condition in EVENT_DATE_CHECKS:
        op.create_check_constraint(name, EVENT_TABLE, condition)

    op.execute(
        f"UPDATE {BOOKING_TABLE} SET status = 'REGISTERED' WHERE status = 'DRAFT'"
    )
    _swap_booking_status_enum(booking_status_without_draft)


def downgrade() -> None:
    _swap_booking_status_enum(booking_status_with_draft)

    for name, _ in reversed(EVENT_DATE_CHECKS):
        op.drop_constraint(name, EVENT_TABLE, type_="check")
