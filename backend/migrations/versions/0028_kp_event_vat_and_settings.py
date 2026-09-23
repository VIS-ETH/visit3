"""KP event VAT rate, terms link and notification settings

Revision ID: 0028
Revises: 0027
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0028"
down_revision: Union[str, Sequence[str], None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "kpevent"
DEFAULT_VAT_RATE_PERMILLE = "81"
DEFAULT_FINALIZATION_REMINDER_DAYS = "3"
BACKFILLED_COLUMNS = ("vat_rate_permille", "finalization_reminder_days")


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "vat_rate_permille",
            sa.Integer(),
            nullable=False,
            server_default=sa.text(DEFAULT_VAT_RATE_PERMILLE),
        ),
    )
    op.add_column(
        TABLE,
        sa.Column("terms_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "notification_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "finalization_reminder_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text(DEFAULT_FINALIZATION_REMINDER_DAYS),
        ),
    )
    for column_name in BACKFILLED_COLUMNS:
        op.alter_column(TABLE, column_name, server_default=None)


def downgrade() -> None:
    op.drop_column(TABLE, "finalization_reminder_days")
    op.drop_column(TABLE, "notification_email")
    op.drop_column(TABLE, "terms_url")
    op.drop_column(TABLE, "vat_rate_permille")
