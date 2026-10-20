from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0059"
down_revision: Union[str, Sequence[str], None] = "0058"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SERVICE_TABLE = "kpeventservice"
INCLUSION_TABLE = "kpeventserviceinclusion"
EXCLUSION_TABLE = "kpeventserviceexclusion"


def timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        INCLUSION_TABLE,
        *timestamps(),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("included_service_id", sa.Uuid(), nullable=False),
        sa.Column("included_quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], [f"{SERVICE_TABLE}.id"]),
        sa.ForeignKeyConstraint(["included_service_id"], [f"{SERVICE_TABLE}.id"]),
        sa.PrimaryKeyConstraint("service_id", "included_service_id"),
    )
    op.create_table(
        EXCLUSION_TABLE,
        *timestamps(),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("excluded_service_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], [f"{SERVICE_TABLE}.id"]),
        sa.ForeignKeyConstraint(["excluded_service_id"], [f"{SERVICE_TABLE}.id"]),
        sa.PrimaryKeyConstraint("service_id", "excluded_service_id"),
    )


def downgrade() -> None:
    op.drop_table(EXCLUSION_TABLE)
    op.drop_table(INCLUSION_TABLE)
