from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0048"
down_revision: Union[str, Sequence[str], None] = "0047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "emailchangetoken"


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("pending_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.create_table(
        TABLE,
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
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("new_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_emailchangetoken_expires_at"), TABLE, ["expires_at"], unique=False
    )
    op.create_index(op.f("ix_emailchangetoken_token"), TABLE, ["token"], unique=True)
    op.create_index(
        op.f("ix_emailchangetoken_user_id"), TABLE, ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_emailchangetoken_user_id"), table_name=TABLE)
    op.drop_index(op.f("ix_emailchangetoken_token"), table_name=TABLE)
    op.drop_index(op.f("ix_emailchangetoken_expires_at"), table_name=TABLE)
    op.drop_table(TABLE)
    op.drop_column("user", "pending_email")
