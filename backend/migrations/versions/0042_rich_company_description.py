from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0042"
down_revision: Union[str, Sequence[str], None] = "0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("kpcompanyprofile", "kpbookingcompanydetails")
COLUMN = "description"
PLAIN_LENGTH = 2500
ENTITIES = (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#x27;", "'"))


def plain_text_expression() -> str:
    expression = rf"regexp_replace({COLUMN}, '</p>\s*<p>|<br\s*/?>', E'\n', 'gi')"
    expression = f"regexp_replace({expression}, '<[^>]*>', '', 'g')"
    for entity, character in ENTITIES:
        expression = f"replace({expression}, '{entity}', $${character}$$)"
    return f"left(replace({expression}, '&amp;', '&'), {PLAIN_LENGTH})"


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(
            table,
            COLUMN,
            existing_type=sqlmodel.sql.sqltypes.AutoString(length=PLAIN_LENGTH),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(
            f"UPDATE {table} SET {COLUMN} = {plain_text_expression()} "
            f"WHERE {COLUMN} LIKE '<%'"
        )
        op.alter_column(
            table,
            COLUMN,
            existing_type=sa.Text(),
            type_=sqlmodel.sql.sqltypes.AutoString(length=PLAIN_LENGTH),
            existing_nullable=False,
        )
