from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0058"
down_revision: Union[str, Sequence[str], None] = "0057"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REMOVED_TEMPLATE_KEYS = ("account_confirmed", "account_awaiting_confirmation")


def upgrade() -> None:
    op.add_column(
        "company",
        sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute("UPDATE company SET confirmed_at = created_at")
    op.drop_column("user", "user_confirmed")
    for key in REMOVED_TEMPLATE_KEYS:
        op.execute(f"DELETE FROM mailtemplate WHERE key = '{key}'")


def downgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "user_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.drop_column("company", "confirmed_at")
