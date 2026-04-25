"""replace booking finalized with status

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-25 19:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


booking_status_enum = postgresql.ENUM(
    "draft",
    "confirmed",
    "finalized",
    "cancelled",
    name="kpbookingstatus",
)


def upgrade() -> None:
    """Upgrade schema."""
    booking_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "kpeventbooking",
        sa.Column(
            "status",
            booking_status_enum,
            nullable=False,
            server_default="confirmed",
        ),
    )
    op.execute(
        """
        UPDATE kpeventbooking
        SET status = CASE
            WHEN finalized THEN 'finalized'::kpbookingstatus
            ELSE 'confirmed'::kpbookingstatus
        END
        """
    )
    op.alter_column("kpeventbooking", "status", server_default=None)
    op.drop_column("kpeventbooking", "finalized")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "kpeventbooking",
        sa.Column("finalized", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE kpeventbooking
        SET finalized = CASE
            WHEN status = 'finalized'::kpbookingstatus THEN TRUE
            ELSE FALSE
        END
        """
    )
    op.alter_column("kpeventbooking", "finalized", server_default=None)
    op.drop_column("kpeventbooking", "status")
    booking_status_enum.drop(op.get_bind(), checkfirst=True)
