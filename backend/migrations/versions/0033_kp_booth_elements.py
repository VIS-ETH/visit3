"""KP booth elements, zone layouts and nametag cap

Revision ID: 0033
Revises: 0032
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0033"
down_revision: Union[str, Sequence[str], None] = "0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EVENT_TABLE = "kpevent"
SERVICE_TABLE = "kpeventservice"
ZONE_TABLE = "kpeventboothzone"
LAYOUT_FK = "kpeventboothzone_layout_stored_file_id_fkey"
LAYOUT_UQ = "kpeventboothzone_layout_stored_file_id_key"
CATEGORY_TYPE_NAME = "kpservicecategory"
DEFAULT_CATEGORY = "SERVICE"
DEFAULT_MAX_NAMETAGS_PER_BOOKING = "10"
LAYOUT_DESCRIPTION_MAX_LENGTH = 2000

service_category = postgresql.ENUM("SERVICE", "BOOTH_ELEMENT", name=CATEGORY_TYPE_NAME)
service_category_column = postgresql.ENUM(
    "SERVICE", "BOOTH_ELEMENT", name=CATEGORY_TYPE_NAME, create_type=False
)


def upgrade() -> None:
    service_category.create(op.get_bind(), checkfirst=True)
    op.add_column(
        SERVICE_TABLE,
        sa.Column(
            "category",
            service_category_column,
            nullable=False,
            server_default=DEFAULT_CATEGORY,
        ),
    )
    op.alter_column(SERVICE_TABLE, "category", server_default=None)
    op.add_column(
        SERVICE_TABLE,
        sa.Column("unit_label", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        ZONE_TABLE,
        sa.Column(
            "layout_description",
            sqlmodel.sql.sqltypes.AutoString(length=LAYOUT_DESCRIPTION_MAX_LENGTH),
            nullable=True,
        ),
    )
    op.add_column(
        ZONE_TABLE,
        sa.Column("layout_stored_file_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        LAYOUT_FK,
        ZONE_TABLE,
        "storedfile",
        ["layout_stored_file_id"],
        ["id"],
    )
    op.create_unique_constraint(LAYOUT_UQ, ZONE_TABLE, ["layout_stored_file_id"])
    op.add_column(
        EVENT_TABLE,
        sa.Column(
            "max_nametags_per_booking",
            sa.Integer(),
            nullable=False,
            server_default=sa.text(DEFAULT_MAX_NAMETAGS_PER_BOOKING),
        ),
    )
    op.alter_column(EVENT_TABLE, "max_nametags_per_booking", server_default=None)


def downgrade() -> None:
    op.drop_column(EVENT_TABLE, "max_nametags_per_booking")
    op.drop_constraint(LAYOUT_UQ, ZONE_TABLE, type_="unique")
    op.drop_constraint(LAYOUT_FK, ZONE_TABLE, type_="foreignkey")
    op.drop_column(ZONE_TABLE, "layout_stored_file_id")
    op.drop_column(ZONE_TABLE, "layout_description")
    op.drop_column(SERVICE_TABLE, "unit_label")
    op.drop_column(SERVICE_TABLE, "category")
    service_category.drop(op.get_bind(), checkfirst=True)
