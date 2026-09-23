"""company profile

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-18 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027"
down_revision: Union[str, Sequence[str], None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROFILE_TABLE = "kpcompanyprofile"
SNAPSHOT_TABLE = "kpbookingcompanydetails"
SNAPSHOT_LINK_TABLE = "kpbookingcompanydetailsindustrylink"
SNAPSHOT_LINK_FK = "kpbookingcompanydetailsindustrylink_industry_id_fkey"
LOGO_FK = "kpcompanyprofile_logo_stored_file_id_fkey"
LOGO_UNIQUE = "kpcompanyprofile_logo_stored_file_id_key"

BILLING_TEXT_COLUMNS = (
    "billing_company_name",
    "billing_street",
    "billing_house_number",
    "billing_postal_code",
    "billing_city",
)
OFFER_COLUMNS = (
    "offers_internships",
    "offers_part_time",
    "offers_theses",
    "offers_graduate_positions",
)
EMPLOYEE_COUNT_COLUMNS = ("employee_count_switzerland", "employee_count_worldwide")
OPTIONAL_TEXT_COLUMNS = (
    "website",
    "contact_phone",
    "billing_vat_number",
    "billing_email",
)
PROFILE_REQUIRED_TEXT_COLUMNS = ("brand_name", "contact_person", "places_of_work")
SNAPSHOT_LEGACY_COLUMNS = (
    ("profile", sqlmodel.sql.sqltypes.AutoString(), "''"),
    ("address", sqlmodel.sql.sqltypes.AutoString(), "''"),
    ("employees_count", sa.Integer(), None),
    ("employees_count_switzerland", sa.Integer(), None),
    ("offer_internship", sa.Boolean(), "false"),
    ("offer_part_time", sa.Boolean(), "false"),
    ("offer_thesis", sa.Boolean(), "false"),
)


def language_array() -> postgresql.ARRAY:
    return postgresql.ARRAY(
        postgresql.ENUM(
            "ENGLISH",
            "GERMAN",
            "FRENCH",
            "ITALIAN",
            name="kpcompanylanguage",
            create_type=False,
        )
    )


def add_column_with_backfill(
    table: str, column: sa.Column[object], server_default: str
) -> None:
    column.server_default = sa.text(server_default)
    op.add_column(table, column)
    op.alter_column(table, str(column.name), server_default=None)


def add_text_column(table: str, name: str, length: int | None = None) -> None:
    add_column_with_backfill(
        table,
        sa.Column(name, sqlmodel.sql.sqltypes.AutoString(length=length), nullable=False),
        "''",
    )


def add_shared_profile_columns(table: str) -> None:
    for name in OPTIONAL_TEXT_COLUMNS:
        op.add_column(
            table, sa.Column(name, sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
    for name in EMPLOYEE_COUNT_COLUMNS:
        op.add_column(table, sa.Column(name, sa.Integer(), nullable=True))
    add_text_column(table, "description", length=600)
    for name in BILLING_TEXT_COLUMNS:
        add_text_column(table, name)
    add_text_column(table, "billing_country", length=2)
    for name in OFFER_COLUMNS:
        add_column_with_backfill(
            table, sa.Column(name, sa.Boolean(), nullable=False), "false"
        )


def drop_shared_profile_columns(table: str) -> None:
    for name in OFFER_COLUMNS:
        op.drop_column(table, name)
    op.drop_column(table, "billing_country")
    for name in BILLING_TEXT_COLUMNS:
        op.drop_column(table, name)
    op.drop_column(table, "description")
    for name in EMPLOYEE_COUNT_COLUMNS:
        op.drop_column(table, name)
    for name in OPTIONAL_TEXT_COLUMNS:
        op.drop_column(table, name)


def create_industry_tables() -> None:
    op.create_table(
        "industry",
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
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_industry_name",
        "industry",
        ["name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "kpcompanyprofileindustrylink",
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("industry_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["kpcompanyprofile.id"]),
        sa.ForeignKeyConstraint(["industry_id"], ["industry.id"]),
        sa.PrimaryKeyConstraint("profile_id", "industry_id"),
    )


def upgrade_profile_table() -> None:
    add_shared_profile_columns(PROFILE_TABLE)
    for name in PROFILE_REQUIRED_TEXT_COLUMNS:
        add_text_column(PROFILE_TABLE, name)
    op.add_column(
        PROFILE_TABLE, sa.Column("logo_stored_file_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        LOGO_FK, PROFILE_TABLE, "storedfile", ["logo_stored_file_id"], ["id"]
    )
    op.create_unique_constraint(LOGO_UNIQUE, PROFILE_TABLE, ["logo_stored_file_id"])
    add_column_with_backfill(
        PROFILE_TABLE,
        sa.Column("languages", language_array(), nullable=False),
        "'{}'::kpcompanylanguage[]",
    )
    op.add_column(
        PROFILE_TABLE,
        sa.Column(
            "profile_completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
    )
    op.execute("UPDATE kpcompanyprofile SET billing_street = invoice_address")
    op.drop_column(PROFILE_TABLE, "invoice_address")


def upgrade_snapshot_table() -> None:
    add_shared_profile_columns(SNAPSHOT_TABLE)
    op.add_column(
        SNAPSHOT_TABLE,
        sa.Column("contact_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    add_text_column(SNAPSHOT_TABLE, "shipping_address")
    add_column_with_backfill(
        SNAPSHOT_TABLE,
        sa.Column("confirmed_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        "now()",
    )
    op.execute("UPDATE kpbookingcompanydetails SET description = profile")
    for name, _, _ in SNAPSHOT_LEGACY_COLUMNS:
        op.drop_column(SNAPSHOT_TABLE, name)


def downgrade_snapshot_table() -> None:
    for name, column_type, server_default in SNAPSHOT_LEGACY_COLUMNS:
        if server_default is None:
            op.add_column(SNAPSHOT_TABLE, sa.Column(name, column_type, nullable=True))
        else:
            add_column_with_backfill(
                SNAPSHOT_TABLE,
                sa.Column(name, column_type, nullable=False),
                server_default,
            )
    op.execute("UPDATE kpbookingcompanydetails SET profile = description")
    op.drop_column(SNAPSHOT_TABLE, "confirmed_at")
    op.drop_column(SNAPSHOT_TABLE, "shipping_address")
    op.drop_column(SNAPSHOT_TABLE, "contact_email")
    drop_shared_profile_columns(SNAPSHOT_TABLE)


def downgrade_profile_table() -> None:
    add_text_column(PROFILE_TABLE, "invoice_address")
    op.execute("UPDATE kpcompanyprofile SET invoice_address = billing_street")
    op.drop_column(PROFILE_TABLE, "profile_completed_at")
    op.drop_column(PROFILE_TABLE, "languages")
    op.drop_constraint(LOGO_UNIQUE, PROFILE_TABLE, type_="unique")
    op.drop_constraint(LOGO_FK, PROFILE_TABLE, type_="foreignkey")
    op.drop_column(PROFILE_TABLE, "logo_stored_file_id")
    for name in PROFILE_REQUIRED_TEXT_COLUMNS:
        op.drop_column(PROFILE_TABLE, name)
    drop_shared_profile_columns(PROFILE_TABLE)


def freeze_snapshot_industry_names() -> None:
    op.add_column(
        SNAPSHOT_LINK_TABLE,
        sa.Column("industry_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.execute(
        "UPDATE kpbookingcompanydetailsindustrylink AS link "
        "SET industry_name = kpindustry.name "
        "FROM kpindustry WHERE kpindustry.id = link.industry_id"
    )
    op.execute(
        "UPDATE kpbookingcompanydetailsindustrylink "
        "SET industry_name = '' WHERE industry_name IS NULL"
    )
    op.alter_column(SNAPSHOT_LINK_TABLE, "industry_name", nullable=False)


INDUSTRY_COLUMNS = "id, name, created_at, updated_at, deleted_at"


def copy_rows_between_industry_tables(source: str, target: str) -> None:
    op.execute(
        f"INSERT INTO {target} ({INDUSTRY_COLUMNS}) "
        f"SELECT {INDUSTRY_COLUMNS} FROM {source} "
        f"WHERE id NOT IN (SELECT id FROM {target})"
    )


def upgrade() -> None:
    create_industry_tables()
    copy_rows_between_industry_tables("kpindustry", "industry")
    upgrade_profile_table()
    upgrade_snapshot_table()
    freeze_snapshot_industry_names()
    op.execute(
        "ALTER TABLE kpbookingcompanydetailsindustrylink "
        f"DROP CONSTRAINT IF EXISTS {SNAPSHOT_LINK_FK}"
    )
    op.create_foreign_key(
        SNAPSHOT_LINK_FK, SNAPSHOT_LINK_TABLE, "industry", ["industry_id"], ["id"]
    )


def downgrade() -> None:
    copy_rows_between_industry_tables("industry", "kpindustry")
    op.drop_column(SNAPSHOT_LINK_TABLE, "industry_name")
    op.drop_constraint(SNAPSHOT_LINK_FK, SNAPSHOT_LINK_TABLE, type_="foreignkey")
    op.create_foreign_key(
        SNAPSHOT_LINK_FK, SNAPSHOT_LINK_TABLE, "kpindustry", ["industry_id"], ["id"]
    )
    downgrade_snapshot_table()
    downgrade_profile_table()
    op.drop_table("kpcompanyprofileindustrylink")
    op.drop_index("ix_industry_name", table_name="industry")
    op.drop_table("industry")
