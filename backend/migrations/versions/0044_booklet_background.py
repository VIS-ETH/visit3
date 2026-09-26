from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0044"
down_revision: Union[str, Sequence[str], None] = "0043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "kpevent"
COLUMN = "booklet_background_stored_file_id"
FOREIGN_KEY = "kpevent_booklet_background_stored_file_id_fkey"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column(COLUMN, sa.Uuid(), nullable=True))
    op.create_foreign_key(FOREIGN_KEY, TABLE, "storedfile", [COLUMN], ["id"])


def downgrade() -> None:
    op.drop_constraint(FOREIGN_KEY, TABLE, type_="foreignkey")
    op.drop_column(TABLE, COLUMN)
