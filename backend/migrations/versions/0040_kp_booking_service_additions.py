from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0040"
down_revision: Union[str, Sequence[str], None] = "0039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "kpeventbookingservice"
COLUMN = "added_after_confirmation"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(COLUMN, sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.alter_column(TABLE, COLUMN, server_default=None)


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
