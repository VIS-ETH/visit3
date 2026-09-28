from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0049"
down_revision: Union[str, Sequence[str], None] = "0048"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BANNER_TABLE = "kpeventbanner"
VARIANT_TABLE = "kpeventbannervariant"
EVENT_TABLE = "kpevent"
EVENT_COLUMN = "banner_id"
EVENT_FOREIGN_KEY = "kpevent_banner_id_fkey"


def timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        BANNER_TABLE,
        *timestamps(),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        VARIANT_TABLE,
        *timestamps(),
        sa.Column("banner_id", sa.Uuid(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("stored_file_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["banner_id"], [f"{BANNER_TABLE}.id"]),
        sa.ForeignKeyConstraint(["stored_file_id"], ["storedfile.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_file_id"),
    )
    op.create_index(
        op.f("ix_kpeventbannervariant_banner_id"),
        VARIANT_TABLE,
        ["banner_id"],
        unique=False,
    )
    op.add_column(EVENT_TABLE, sa.Column(EVENT_COLUMN, sa.Uuid(), nullable=True))
    op.create_foreign_key(
        EVENT_FOREIGN_KEY, EVENT_TABLE, BANNER_TABLE, [EVENT_COLUMN], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(EVENT_FOREIGN_KEY, EVENT_TABLE, type_="foreignkey")
    op.drop_column(EVENT_TABLE, EVENT_COLUMN)
    op.drop_index(op.f("ix_kpeventbannervariant_banner_id"), table_name=VARIANT_TABLE)
    op.drop_table(VARIANT_TABLE)
    op.drop_table(BANNER_TABLE)
