"""uppercase kp booking status

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-03 15:45:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_enum_value_if_exists(old_value: str, new_value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'kpbookingstatus'
                  AND e.enumlabel = '{old_value}'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'kpbookingstatus'
                  AND e.enumlabel = '{new_value}'
            )
            THEN
                ALTER TYPE kpbookingstatus RENAME VALUE '{old_value}' TO '{new_value}';
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    """Upgrade schema."""
    _rename_enum_value_if_exists("draft", "DRAFT")
    _rename_enum_value_if_exists("registered", "REGISTERED")
    _rename_enum_value_if_exists("finalized", "FINALIZED")
    _rename_enum_value_if_exists("confirmed", "CONFIRMED")
    _rename_enum_value_if_exists("cancelled", "CANCELLED")


def downgrade() -> None:
    """Downgrade schema."""
    _rename_enum_value_if_exists("DRAFT", "draft")
    _rename_enum_value_if_exists("REGISTERED", "registered")
    _rename_enum_value_if_exists("FINALIZED", "finalized")
    _rename_enum_value_if_exists("CONFIRMED", "confirmed")
    _rename_enum_value_if_exists("CANCELLED", "cancelled")
