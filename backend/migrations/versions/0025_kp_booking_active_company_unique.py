"""kp booking active company unique

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-16 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0025"
down_revision: Union[str, Sequence[str], None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_kpeventbooking_active_company",
        "kpeventbooking",
        ["event_id", "company_id"],
        unique=True,
        postgresql_where=sa.text("status != 'CANCELLED'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_kpeventbooking_active_company",
        table_name="kpeventbooking",
    )
