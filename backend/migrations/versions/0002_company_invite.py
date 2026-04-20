"""company invite

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-20

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companyinvite",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("invited_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_companyinvite_token"), "companyinvite", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_companyinvite_token"), table_name="companyinvite")
    op.drop_table("companyinvite")
