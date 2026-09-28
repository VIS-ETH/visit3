from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0047"
down_revision: Union[str, Sequence[str], None] = "0046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "companyinvite"
COLUMN = "invited_by_user_id"
INDEX = "ix_companyinvite_invited_by_user_id"
FOREIGN_KEY = "companyinvite_invited_by_user_id_fkey"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column(COLUMN, sa.Uuid(), nullable=True))
    op.create_foreign_key(FOREIGN_KEY, TABLE, "user", [COLUMN], ["id"])
    op.create_index(INDEX, TABLE, [COLUMN], unique=False)
    op.execute(
        f"UPDATE {TABLE} SET token = encode(sha256(convert_to(token, 'UTF8')), 'hex')"
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM {TABLE} WHERE NOT is_used")
    op.drop_index(INDEX, table_name=TABLE)
    op.drop_constraint(FOREIGN_KEY, TABLE, type_="foreignkey")
    op.drop_column(TABLE, COLUMN)
