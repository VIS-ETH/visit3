"""KP venue layouts

Revision ID: 0032
Revises: 0031
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032"
down_revision: Union[str, Sequence[str], None] = "0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAYOUT_TABLE = "kpvenuelayout"
SHAPE_TABLE = "kpvenuezoneshape"
BOOTH_TABLE = "kpvenuebooth"
LAYOUT_NAME_IX = "ix_kpvenuelayout_event_id_name"
BOOTH_NR_IX = "ix_kpvenuebooth_layout_id_booth_nr"
NOT_DELETED = sa.text("deleted_at IS NULL")


def _base_columns() -> list[sa.Column[sa.types.TypeEngine[object]]]:
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
        LAYOUT_TABLE,
        *_base_columns(),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("background_stored_file_id", sa.Uuid(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["kpevent.id"]),
        sa.ForeignKeyConstraint(["background_stored_file_id"], ["storedfile.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("background_stored_file_id"),
    )
    op.create_index(
        LAYOUT_NAME_IX,
        LAYOUT_TABLE,
        ["event_id", "name"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )
    op.create_table(
        SHAPE_TABLE,
        *_base_columns(),
        sa.Column("layout_id", sa.Uuid(), nullable=False),
        sa.Column("booth_zone_id", sa.Uuid(), nullable=False),
        sa.Column("shape", sa.JSON(), nullable=False),
        sa.Column("label_position", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["layout_id"], ["kpvenuelayout.id"]),
        sa.ForeignKeyConstraint(["booth_zone_id"], ["kpeventboothzone.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        BOOTH_TABLE,
        *_base_columns(),
        sa.Column("layout_id", sa.Uuid(), nullable=False),
        sa.Column("booth_zone_id", sa.Uuid(), nullable=False),
        sa.Column("booth_nr", sa.Integer(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("rotation", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["layout_id"], ["kpvenuelayout.id"]),
        sa.ForeignKeyConstraint(["booth_zone_id"], ["kpeventboothzone.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        BOOTH_NR_IX,
        BOOTH_TABLE,
        ["layout_id", "booth_nr"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )


def downgrade() -> None:
    op.drop_index(BOOTH_NR_IX, table_name=BOOTH_TABLE)
    op.drop_table(BOOTH_TABLE)
    op.drop_table(SHAPE_TABLE)
    op.drop_index(LAYOUT_NAME_IX, table_name=LAYOUT_TABLE)
    op.drop_table(LAYOUT_TABLE)
