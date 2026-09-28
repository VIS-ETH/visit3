from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0050"
down_revision: Union[str, Sequence[str], None] = "0049"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "kpeventboothzone"
COLUMN = "registration_open"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(COLUMN, sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column(TABLE, COLUMN, server_default=None)


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
