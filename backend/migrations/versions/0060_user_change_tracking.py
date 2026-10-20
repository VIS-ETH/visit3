from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0060"
down_revision: Union[str, Sequence[str], None] = "0059"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "user"
COLUMNS = ("previous_login_at", "changes_seen_at")


def upgrade() -> None:
    for column in COLUMNS:
        op.add_column(
            TABLE,
            sa.Column(column, postgresql.TIMESTAMP(timezone=True), nullable=True),
        )


def downgrade() -> None:
    for column in reversed(COLUMNS):
        op.drop_column(TABLE, column)
