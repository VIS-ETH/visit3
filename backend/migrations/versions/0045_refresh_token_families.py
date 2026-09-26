from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0045"
down_revision: Union[str, Sequence[str], None] = "0044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "refreshtoken"
FAMILY = "family_id"
FAMILY_INDEX = "ix_refreshtoken_family_id"
IDP_TOKEN = "idp_refresh_token"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column(FAMILY, sa.Uuid(), nullable=True))
    op.execute(f"UPDATE {TABLE} SET {FAMILY} = id")
    op.alter_column(TABLE, FAMILY, existing_type=sa.Uuid(), nullable=False)
    op.create_index(FAMILY_INDEX, TABLE, [FAMILY], unique=False)
    op.add_column(TABLE, sa.Column(IDP_TOKEN, sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column(TABLE, IDP_TOKEN)
    op.drop_index(FAMILY_INDEX, table_name=TABLE)
    op.drop_column(TABLE, FAMILY)
