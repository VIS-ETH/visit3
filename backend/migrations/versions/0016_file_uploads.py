"""file uploads

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-02 10:56:53.877434

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE kpeventnametagbackground
        DROP CONSTRAINT IF EXISTS kpeventnametagbackground_event_id_key
        """
    )
    op.execute(
        """
        ALTER TABLE storedfile
        DROP CONSTRAINT IF EXISTS storedfile_storage_key_key
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_unique_constraint(
        op.f("storedfile_storage_key_key"),
        "storedfile",
        ["storage_key"],
        postgresql_nulls_not_distinct=False,
    )
    op.drop_column("storedfile", "sha256")
    op.create_unique_constraint(
        op.f("kpeventnametagbackground_event_id_key"),
        "kpeventnametagbackground",
        ["event_id"],
        postgresql_nulls_not_distinct=False,
    )
