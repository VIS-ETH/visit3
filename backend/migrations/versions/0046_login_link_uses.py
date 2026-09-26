from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0046"
down_revision: Union[str, Sequence[str], None] = "0045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "loginlinktoken"
COLUMN = "use_count"
MAX_USES = 3


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(COLUMN, sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        f"UPDATE {TABLE} SET {COLUMN} = {MAX_USES} "
        "WHERE used_at IS NOT NULL OR is_revoked"
    )


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
