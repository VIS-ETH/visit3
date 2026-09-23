"""mail templates and login link tokens

Revision ID: 0030
Revises: 0029
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: Union[str, Sequence[str], None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MAIL_TEMPLATE_TABLE = "mailtemplate"
LOGIN_LINK_TABLE = "loginlinktoken"


def upgrade() -> None:
    op.create_table(
        MAIL_TEMPLATE_TABLE,
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
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("subject_de", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("subject_en", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("body_de", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("body_en", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mailtemplate_key"), MAIL_TEMPLATE_TABLE, ["key"], unique=True
    )
    op.create_index(
        op.f("ix_mailtemplate_updated_by_user_id"),
        MAIL_TEMPLATE_TABLE,
        ["updated_by_user_id"],
        unique=False,
    )

    op.create_table(
        LOGIN_LINK_TABLE,
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
        sa.Column(
            "expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.Column("target_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_loginlinktoken_expires_at"),
        LOGIN_LINK_TABLE,
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_loginlinktoken_token"), LOGIN_LINK_TABLE, ["token"], unique=True
    )
    op.create_index(
        op.f("ix_loginlinktoken_user_id"), LOGIN_LINK_TABLE, ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_loginlinktoken_user_id"), table_name=LOGIN_LINK_TABLE)
    op.drop_index(op.f("ix_loginlinktoken_token"), table_name=LOGIN_LINK_TABLE)
    op.drop_index(op.f("ix_loginlinktoken_expires_at"), table_name=LOGIN_LINK_TABLE)
    op.drop_table(LOGIN_LINK_TABLE)
    op.drop_index(
        op.f("ix_mailtemplate_updated_by_user_id"), table_name=MAIL_TEMPLATE_TABLE
    )
    op.drop_index(op.f("ix_mailtemplate_key"), table_name=MAIL_TEMPLATE_TABLE)
    op.drop_table(MAIL_TEMPLATE_TABLE)
