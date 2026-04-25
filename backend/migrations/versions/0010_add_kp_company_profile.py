"""add kp company profile

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-25 18:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "kpcompanyprofile",
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column(
            "invoice_address", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "shipping_address", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("contact_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("kp_contact_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["kp_contact_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("kpcompanyprofile")
