from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0041"
down_revision: Union[str, Sequence[str], None] = "0040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAYOUT_TABLE = "kpvenuelayout"
COLUMN = "floor_plan"
TYPE_NAME = "kpvenuefloorplan"
FLOOR_PLANS = ("MAIN_HALL", "RED_HALL")

floor_plan_type = postgresql.ENUM(*FLOOR_PLANS, name=TYPE_NAME)
floor_plan_column = postgresql.ENUM(*FLOOR_PLANS, name=TYPE_NAME, create_type=False)


def upgrade() -> None:
    floor_plan_type.create(op.get_bind(), checkfirst=True)
    op.add_column(LAYOUT_TABLE, sa.Column(COLUMN, floor_plan_column, nullable=True))


def downgrade() -> None:
    op.drop_column(LAYOUT_TABLE, COLUMN)
    floor_plan_type.drop(op.get_bind(), checkfirst=True)
