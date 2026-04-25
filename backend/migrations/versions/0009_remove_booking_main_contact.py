"""remove booking main contact

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-25 18:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        "kpeventbooking_main_contact_id_fkey",
        "kpeventbooking",
        type_="foreignkey",
    )
    op.drop_column("kpeventbooking", "main_contact_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "kpeventbooking",
        sa.Column("main_contact_id", sa.Uuid(), nullable=False),
    )
    op.create_foreign_key(
        "kpeventbooking_main_contact_id_fkey",
        "kpeventbooking",
        "user",
        ["main_contact_id"],
        ["id"],
    )
