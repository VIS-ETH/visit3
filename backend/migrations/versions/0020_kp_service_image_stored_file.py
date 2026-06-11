"""KP service image stored file

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020"
down_revision: Union[str, Sequence[str], None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_NAME = "kpeventservice_image_stored_file_id_fkey"


def upgrade() -> None:
    op.add_column(
        "kpeventservice",
        sa.Column("image_stored_file_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        FK_NAME,
        "kpeventservice",
        "storedfile",
        ["image_stored_file_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "kpeventservice_image_stored_file_id_key",
        "kpeventservice",
        ["image_stored_file_id"],
    )
    op.drop_column("kpeventservice", "image_url")


def downgrade() -> None:
    op.add_column(
        "kpeventservice",
        sa.Column("image_url", sa.String(), nullable=True),
    )
    op.drop_constraint(
        "kpeventservice_image_stored_file_id_key", "kpeventservice", type_="unique"
    )
    op.drop_constraint(FK_NAME, "kpeventservice", type_="foreignkey")
    op.drop_column("kpeventservice", "image_stored_file_id")
