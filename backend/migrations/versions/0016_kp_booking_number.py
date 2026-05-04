"""KP Booking Number

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-01 09:50:59.091903

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEQ_NAME = "kpeventbooking_booking_number_seq"
BOOKING_NUMBER_UQ = "kpeventbooking_booking_number_key"


def upgrade() -> None:
    op.execute(
        sa.text(
            f'CREATE SEQUENCE "{SEQ_NAME}" INCREMENT BY 1 MINVALUE 1000 START WITH 1000'
        )
    )
    op.add_column(
        "kpeventbooking",
        sa.Column("booking_number", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            f"ALTER TABLE kpeventbooking ALTER COLUMN booking_number "
            f"SET DEFAULT nextval('{SEQ_NAME}'::regclass)"
        )
    )
    # Keep existing rows and assign numbers from the new sequence.
    op.execute(
        sa.text(
            "UPDATE kpeventbooking "
            f"SET booking_number = nextval('{SEQ_NAME}'::regclass) "
            "WHERE booking_number IS NULL"
        )
    )
    op.alter_column(
        "kpeventbooking",
        "booking_number",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_unique_constraint(
        BOOKING_NUMBER_UQ,
        "kpeventbooking",
        ["booking_number"],
    )
    op.execute(
        sa.text(f'ALTER SEQUENCE "{SEQ_NAME}" OWNED BY kpeventbooking.booking_number')
    )


def downgrade() -> None:
    op.drop_constraint(BOOKING_NUMBER_UQ, "kpeventbooking", type_="unique")
    op.execute(
        sa.text("ALTER TABLE kpeventbooking ALTER COLUMN booking_number DROP DEFAULT")
    )
    op.drop_column("kpeventbooking", "booking_number")
    op.execute(sa.text(f'DROP SEQUENCE IF EXISTS "{SEQ_NAME}"'))
