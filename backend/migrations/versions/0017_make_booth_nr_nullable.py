"""Make booth_nr nullable

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-28 13:21:22.985412

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa


revision: str = "0017"
down_revision: Union[str, Sequence[str], None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "kpeventbooking", "booth_nr", existing_type=sa.INTEGER(), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "kpeventbooking", "booth_nr", existing_type=sa.INTEGER(), nullable=False
    )
