"""initial

Revision ID: 0001
Revises:
Create Date: 2026-04-17

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "role",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_role_name"), "role", ["name"], unique=True)

    op.create_table(
        "company",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_company_name"), "company", ["name"], unique=True)

    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sub", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("password", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("first_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("last_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("user_confirmed", sa.Boolean(), nullable=False),
        sa.Column("email_confirmed", sa.Boolean(), nullable=False),
        sa.Column("is_staff", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("is_company", sa.Boolean(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("phone_number", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)
    op.create_index(op.f("ix_user_sub"), "user", ["sub"], unique=False)

    op.create_table(
        "confirmemailtoken",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_confirmemailtoken_id"), "confirmemailtoken", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_confirmemailtoken_token"), "confirmemailtoken", ["token"], unique=True
    )
    op.create_index(
        op.f("ix_confirmemailtoken_user_id"),
        "confirmemailtoken",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "forgetpasswordtoken",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_forgetpasswordtoken_id"), "forgetpasswordtoken", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_forgetpasswordtoken_token"),
        "forgetpasswordtoken",
        ["token"],
        unique=True,
    )
    op.create_index(
        op.f("ix_forgetpasswordtoken_user_id"),
        "forgetpasswordtoken",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "refreshtoken",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refreshtoken_id"), "refreshtoken", ["id"], unique=False)
    op.create_index(
        op.f("ix_refreshtoken_token"), "refreshtoken", ["token"], unique=True
    )
    op.create_index(
        op.f("ix_refreshtoken_user_id"), "refreshtoken", ["user_id"], unique=False
    )

    op.create_table(
        "userrole",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    op.create_table(
        "kpevent",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("registration_open", sa.Date(), nullable=False),
        sa.Column("registration_end", sa.Date(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kpevent_year"), "kpevent", ["year"], unique=True)

    op.create_table(
        "kpeventcompanylink",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["kpevent.id"]),
        sa.PrimaryKeyConstraint("event_id", "company_id"),
    )


def downgrade() -> None:
    op.drop_table("kpeventcompanylink")
    op.drop_index(op.f("ix_kpevent_year"), table_name="kpevent")
    op.drop_table("kpevent")
    op.drop_table("userrole")
    op.drop_index(op.f("ix_refreshtoken_user_id"), table_name="refreshtoken")
    op.drop_index(op.f("ix_refreshtoken_token"), table_name="refreshtoken")
    op.drop_index(op.f("ix_refreshtoken_id"), table_name="refreshtoken")
    op.drop_table("refreshtoken")
    op.drop_index(
        op.f("ix_forgetpasswordtoken_user_id"), table_name="forgetpasswordtoken"
    )
    op.drop_index(
        op.f("ix_forgetpasswordtoken_token"), table_name="forgetpasswordtoken"
    )
    op.drop_index(op.f("ix_forgetpasswordtoken_id"), table_name="forgetpasswordtoken")
    op.drop_table("forgetpasswordtoken")
    op.drop_index(op.f("ix_confirmemailtoken_user_id"), table_name="confirmemailtoken")
    op.drop_index(op.f("ix_confirmemailtoken_token"), table_name="confirmemailtoken")
    op.drop_index(op.f("ix_confirmemailtoken_id"), table_name="confirmemailtoken")
    op.drop_table("confirmemailtoken")
    op.drop_index(op.f("ix_user_sub"), table_name="user")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
    op.drop_index(op.f("ix_company_name"), table_name="company")
    op.drop_table("company")
    op.drop_index(op.f("ix_role_name"), table_name="role")
    op.drop_table("role")
