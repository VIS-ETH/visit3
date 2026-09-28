from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0051"
down_revision: Union[str, Sequence[str], None] = "0050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("kpcompanyprofile", "kpbookingcompanydetails")
COLUMN = "student_contact_email"


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(COLUMN, sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, COLUMN)
