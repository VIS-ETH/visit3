"""add stored file and booking service file link

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-25 20:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: Union[str, Sequence[str], None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "storedfile",
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
        sa.Column("storage_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "original_filename", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("mime_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("etag", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        op.f("ix_storedfile_storage_key"),
        "storedfile",
        ["storage_key"],
        unique=True,
    )
    op.create_table(
        "kpeventbookingservicefilelink",
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
        sa.Column("booking_service_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("stored_file_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["booking_service_id"], ["kpeventbookingservice.id"]),
        sa.ForeignKeyConstraint(["requirement_id"], ["kpeventservicerequirement.id"]),
        sa.ForeignKeyConstraint(["stored_file_id"], ["storedfile.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_service_id", "requirement_id"),
        sa.UniqueConstraint("stored_file_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_storedfile_storage_key"),
        table_name="storedfile",
    )
    op.drop_table("kpeventbookingservicefilelink")
    op.drop_table("storedfile")
