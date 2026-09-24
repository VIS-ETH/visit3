from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0036"
down_revision: Union[str, Sequence[str], None] = "0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROFILE_TABLE = "kpcompanyprofile"
SNAPSHOT_TABLE = "kpbookingcompanydetails"
GENERAL_COLUMNS = ("general_email", "general_phone")

MEMBER = """
    FROM "user" AS u
    WHERE u.company_id = kpcompanyprofile.company_id
    AND u.deleted_at IS NULL
"""

MEMBER_NAMED_AS_CONTACT = f"""
    {MEMBER}
    AND lower(trim(kpcompanyprofile.contact_person))
        = lower(concat_ws(' ', u.first_name, u.last_name))
"""


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE {PROFILE_TABLE} SET kp_contact_user_id = NULL
        WHERE kp_contact_user_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 {MEMBER}
            AND u.id = kpcompanyprofile.kp_contact_user_id)
        """
    )
    op.execute(
        f"""
        UPDATE {PROFILE_TABLE} SET kp_contact_user_id = (
            SELECT u.id {MEMBER}
            AND lower(u.email) = lower(trim(kpcompanyprofile.contact_email))
        )
        WHERE kp_contact_user_id IS NULL
        """
    )
    op.execute(
        f"""
        UPDATE {PROFILE_TABLE} SET kp_contact_user_id = (
            SELECT u.id {MEMBER_NAMED_AS_CONTACT}
        )
        WHERE kp_contact_user_id IS NULL
        AND (SELECT count(*) {MEMBER_NAMED_AS_CONTACT}) = 1
        """
    )
    op.execute(
        f"""
        UPDATE "user" SET phone_number = trim(p.contact_phone)
        FROM {PROFILE_TABLE} AS p
        WHERE p.company_id = "user".company_id
        AND "user".deleted_at IS NULL
        AND "user".phone_number IS NULL
        AND lower("user".email) = lower(trim(p.contact_email))
        AND trim(p.contact_phone) <> ''
        """
    )
    op.alter_column(PROFILE_TABLE, "contact_email", new_column_name="general_email")
    op.alter_column(PROFILE_TABLE, "contact_phone", new_column_name="general_phone")
    op.execute(
        f"""
        UPDATE {PROFILE_TABLE} SET general_email = NULL
        WHERE trim(general_email) = ''
        OR EXISTS (SELECT 1 {MEMBER}
            AND lower(u.email) = lower(trim(kpcompanyprofile.general_email)))
        """
    )
    op.execute(
        f"""
        UPDATE {PROFILE_TABLE} SET general_phone = NULL
        WHERE trim(general_phone) = ''
        OR EXISTS (SELECT 1 {MEMBER}
            AND u.phone_number = trim(kpcompanyprofile.general_phone))
        """
    )
    op.drop_column(PROFILE_TABLE, "contact_person")
    for name in GENERAL_COLUMNS:
        op.add_column(
            SNAPSHOT_TABLE,
            sa.Column(name, sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        )


def downgrade() -> None:
    for name in reversed(GENERAL_COLUMNS):
        op.drop_column(SNAPSHOT_TABLE, name)
    op.add_column(
        PROFILE_TABLE,
        sa.Column(
            "contact_person",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.alter_column(PROFILE_TABLE, "contact_person", server_default=None)
    op.alter_column(PROFILE_TABLE, "general_phone", new_column_name="contact_phone")
    op.alter_column(PROFILE_TABLE, "general_email", new_column_name="contact_email")
    op.execute(
        f"""
        UPDATE {PROFILE_TABLE} SET
            contact_person = coalesce(
                nullif(concat_ws(' ', u.first_name, u.last_name), ''), u.email
            ),
            contact_email = coalesce(contact_email, u.email),
            contact_phone = coalesce(contact_phone, u.phone_number)
        FROM "user" AS u
        WHERE u.id = {PROFILE_TABLE}.kp_contact_user_id
        """
    )
