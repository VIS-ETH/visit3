from typing import Sequence, Union

from alembic import op

revision: str = "0061"
down_revision: Union[str, Sequence[str], None] = "0060"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE kpeventbookingupgradewaitlist SET deleted_at = now() "
        "WHERE deleted_at IS NULL AND booking_id IN "
        "(SELECT id FROM kpeventbooking WHERE deleted_at IS NOT NULL)"
    )


def downgrade() -> None:
    pass
