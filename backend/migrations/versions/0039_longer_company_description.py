from typing import Sequence, Union

import sqlmodel
from alembic import op

revision: str = "0039"
down_revision: Union[str, Sequence[str], None] = "0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("kpcompanyprofile", "kpbookingcompanydetails")
COLUMN = "description"
OLD_LENGTH = 600
NEW_LENGTH = 2500


def resize(length_from: int, length_to: int) -> None:
    for table in TABLES:
        op.alter_column(
            table,
            COLUMN,
            existing_type=sqlmodel.sql.sqltypes.AutoString(length=length_from),
            type_=sqlmodel.sql.sqltypes.AutoString(length=length_to),
            existing_nullable=False,
        )


def upgrade() -> None:
    resize(OLD_LENGTH, NEW_LENGTH)


def downgrade() -> None:
    for table in TABLES:
        op.execute(
            f"UPDATE {table} SET {COLUMN} = left({COLUMN}, {OLD_LENGTH}) "
            f"WHERE length({COLUMN}) > {OLD_LENGTH}"
        )
    resize(NEW_LENGTH, OLD_LENGTH)
