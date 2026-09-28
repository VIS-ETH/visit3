"""KP booking finalization reminder timestamp

Revision ID: 0034
Revises: 0033
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034"
down_revision: Union[str, Sequence[str], None] = "0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "kpeventbooking"
COLUMN = "reminder_sent_at"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(COLUMN, postgresql.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
