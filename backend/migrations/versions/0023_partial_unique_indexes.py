"""Unique user email and company name only among active rows

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: Union[str, Sequence[str], None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOT_DELETED = sa.text("deleted_at IS NULL")
PARTIAL_UNIQUE_INDEXES = [
    ("ix_user_email", "user", "email"),
    ("ix_company_name", "company", "name"),
]


def upgrade() -> None:
    for index_name, table_name, column_name in PARTIAL_UNIQUE_INDEXES:
        op.drop_index(index_name, table_name=table_name)
        op.create_index(
            index_name,
            table_name,
            [column_name],
            unique=True,
            postgresql_where=NOT_DELETED,
        )


def downgrade() -> None:
    for index_name, table_name, column_name in PARTIAL_UNIQUE_INDEXES:
        op.drop_index(index_name, table_name=table_name)
        op.create_index(index_name, table_name, [column_name], unique=True)
