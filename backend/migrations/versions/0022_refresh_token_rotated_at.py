"""Refresh token rotation timestamp

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022"
down_revision: Union[str, Sequence[str], None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "refreshtoken"
COLUMN = "rotated_at"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(COLUMN, postgresql.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
