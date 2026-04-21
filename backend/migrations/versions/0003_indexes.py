"""add missing indexes

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-21

"""

from typing import Sequence, Union

from alembic import op


revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_user_company_id", "user", ["company_id"])

    op.create_index("ix_refreshtoken_expires_at", "refreshtoken", ["expires_at"])
    op.create_index(
        "ix_forgetpasswordtoken_expires_at", "forgetpasswordtoken", ["expires_at"]
    )
    op.create_index(
        "ix_confirmemailtoken_expires_at", "confirmemailtoken", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_company_id", table_name="user")

    op.drop_index("ix_refreshtoken_expires_at", table_name="refreshtoken")
    op.drop_index("ix_forgetpasswordtoken_expires_at", table_name="forgetpasswordtoken")
    op.drop_index("ix_confirmemailtoken_expires_at", table_name="confirmemailtoken")
