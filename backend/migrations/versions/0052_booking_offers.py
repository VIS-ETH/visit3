from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0052"
down_revision: Union[str, Sequence[str], None] = "0051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "kpeventbooking"
COLUMN = "offer_cancel_until"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column(COLUMN, sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
