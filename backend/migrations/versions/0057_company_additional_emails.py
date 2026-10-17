from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0057"
down_revision: Union[str, Sequence[str], None] = "0056"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "kpcompanyprofile"
COLUMN = "additional_emails"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(COLUMN, sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
