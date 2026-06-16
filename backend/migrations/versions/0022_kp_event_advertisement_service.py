"""kp event advertisement service

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-14 21:44:47.965325

"""
from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0022'
down_revision: Union[str, Sequence[str], None] = '0021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_NAME = "kpevent_advertisement_service_id_fkey"
ENUM_NAME = "kpeventservicerequirementtype"
NEW_ENUM_VALUE = "PDF_SINGLE_PAGE"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('kpevent', sa.Column('advertisement_service_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        FK_NAME,
        'kpevent',
        'kpeventservice',
        ['advertisement_service_id'],
        ['id'],
    )
    with op.get_context().autocommit_block():
        op.execute(
            sa.text(
                f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{NEW_ENUM_VALUE}'"
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(FK_NAME, 'kpevent', type_='foreignkey')
    op.drop_column('kpevent', 'advertisement_service_id')
