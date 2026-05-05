"""uppercase kpbookingstatus enum values

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-28 11:37:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: Union[str, Sequence[str], None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RENAMES = [
    ("draft", "DRAFT"),
    ("registered", "REGISTERED"),
    ("finalized", "FINALIZED"),
    ("confirmed", "CONFIRMED"),
    ("cancelled", "CANCELLED"),
]


def upgrade() -> None:
    """Rename all kpbookingstatus values to uppercase."""
    for old, new in _RENAMES:
        op.execute(f"ALTER TYPE kpbookingstatus RENAME VALUE '{old}' TO '{new}'")


def downgrade() -> None:
    """Rename all kpbookingstatus values back to lowercase."""
    for old, new in _RENAMES:
        op.execute(f"ALTER TYPE kpbookingstatus RENAME VALUE '{new}' TO '{old}'")
