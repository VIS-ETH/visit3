"""add kp booking upgrade waitlist

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-25 18:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "kpeventbookingupgradewaitlist",
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
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("target_booth_zone_id", sa.Uuid(), nullable=False),
        sa.Column("priority_rank", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["kpeventbooking.id"]),
        sa.ForeignKeyConstraint(["target_booth_zone_id"], ["kpeventboothzone.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", "target_booth_zone_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("kpeventbookingupgradewaitlist")
