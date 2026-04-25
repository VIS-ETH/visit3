"""update kp booking status flow

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-25 20:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: Union[str, Sequence[str], None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_booking_status_enum = postgresql.ENUM(
    "draft",
    "confirmed",
    "finalized",
    "cancelled",
    name="kpbookingstatus_old",
)

new_booking_status_enum = postgresql.ENUM(
    "draft",
    "registered",
    "finalized",
    "confirmed",
    "cancelled",
    name="kpbookingstatus_new",
)


def upgrade() -> None:
    """Upgrade schema."""
    new_booking_status_enum.create(op.get_bind(), checkfirst=True)
    op.execute(
        """
        ALTER TABLE kpeventbooking
        ALTER COLUMN status TYPE kpbookingstatus_new
        USING (
            CASE status::text
                WHEN 'confirmed' THEN 'registered'
                ELSE status::text
            END
        )::kpbookingstatus_new
        """
    )
    op.execute("DROP TYPE kpbookingstatus")
    op.execute("ALTER TYPE kpbookingstatus_new RENAME TO kpbookingstatus")
    op.alter_column("kpeventbooking", "status", server_default="registered")
    op.alter_column("kpeventbooking", "status", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    old_booking_status_enum.create(op.get_bind(), checkfirst=True)
    op.execute(
        """
        ALTER TABLE kpeventbooking
        ALTER COLUMN status TYPE kpbookingstatus_old
        USING (
            CASE status::text
                WHEN 'registered' THEN 'confirmed'
                ELSE status::text
            END
        )::kpbookingstatus_old
        """
    )
    op.execute("DROP TYPE kpbookingstatus")
    op.execute("ALTER TYPE kpbookingstatus_old RENAME TO kpbookingstatus")
