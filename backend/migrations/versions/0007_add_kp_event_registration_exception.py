"""add kp event registration exception

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-25 12:10:05.629853

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kpeventregistrationexception",
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("allowed_until", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["kpevent.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "company_id"),
    )


def downgrade() -> None:
    op.drop_table("kpeventregistrationexception")
