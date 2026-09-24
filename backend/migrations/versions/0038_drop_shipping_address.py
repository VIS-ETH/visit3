from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0038"
down_revision: Union[str, Sequence[str], None] = "0037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("kpcompanyprofile", "kpbookingcompanydetails")
COLUMN = "shipping_address"


def upgrade() -> None:
    for table in TABLES:
        op.drop_column(table, COLUMN)


def downgrade() -> None:
    for table in reversed(TABLES):
        op.add_column(
            table,
            sa.Column(
                COLUMN,
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default=sa.text("''"),
            ),
        )
        op.alter_column(table, COLUMN, server_default=None)
