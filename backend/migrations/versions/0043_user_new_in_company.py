from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0043"
down_revision: Union[str, Sequence[str], None] = "0042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "user"
COLUMN = "new_in_company_since"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column(COLUMN, sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
