"""KP requirement text answers

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020"
down_revision: Union[str, Sequence[str], None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "kpeventbookingservicefilelink"
CONSTRAINT = "kpeventbookingservicefilelink_exactly_one_answer"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("text_value", sa.String(), nullable=True))
    op.alter_column(
        TABLE,
        "stored_file_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.create_check_constraint(
        CONSTRAINT,
        TABLE,
        "(stored_file_id IS NULL) <> (text_value IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.execute(sa.text(f"DELETE FROM {TABLE} WHERE stored_file_id IS NULL"))
    op.alter_column(
        TABLE,
        "stored_file_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_column(TABLE, "text_value")
