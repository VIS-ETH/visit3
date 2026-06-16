"""kp booking company details languages json

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-16 16:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0026"
down_revision: Union[str, Sequence[str], None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        op.alter_column(
            "kpbookingcompanydetails",
            "languages",
            existing_type=postgresql.ARRAY(
                sa.Enum(
                    "ENGLISH",
                    "GERMAN",
                    "FRENCH",
                    "ITALIAN",
                    name="kpcompanylanguage",
                )
            ),
            type_=sa.JSON(),
            postgresql_using="to_json(languages)::json",
        )
    else:
        # SQLite and other dialects: the model already uses JSON, no change needed.
        pass


def downgrade() -> None:
    """Downgrade schema."""
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        op.alter_column(
            "kpbookingcompanydetails",
            "languages",
            existing_type=sa.JSON(),
            type_=postgresql.ARRAY(
                sa.Enum(
                    "ENGLISH",
                    "GERMAN",
                    "FRENCH",
                    "ITALIAN",
                    name="kpcompanylanguage",
                )
            ),
            postgresql_using="ARRAY(SELECT json_array_elements_text(languages)::kpcompanylanguage)",
        )
    else:
        pass
