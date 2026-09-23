"""0006 Add nametag deadline

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-25 11:41:30.386679

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "kpevent",
        sa.Column(
            "nametags_deadline",
            sa.Date(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.alter_column("kpevent", "nametags_deadline", server_default=None)


def downgrade() -> None:
    op.drop_column("kpevent", "nametags_deadline")
