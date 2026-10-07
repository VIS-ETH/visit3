from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0055"
down_revision: Union[str, Sequence[str], None] = "0054"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CAMPAIGN_TABLE = "mailcampaign"
RECIPIENT_TABLE = "mailcampaignrecipient"
RECIPIENT_UNIQUE = "uq_mailcampaignrecipient_campaign_id_company_id"
STATUS_LENGTH = 32


def timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def optional_timestamp(name: str) -> sa.Column[object]:
    return sa.Column(name, postgresql.TIMESTAMP(timezone=True), nullable=True)


def upgrade() -> None:
    op.create_table(
        CAMPAIGN_TABLE,
        *timestamps(),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("subject_de", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("subject_en", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("body_de", sa.Text(), nullable=False),
        sa.Column("body_en", sa.Text(), nullable=False),
        sa.Column("audience", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=STATUS_LENGTH), nullable=False),
        optional_timestamp("scheduled_at"),
        optional_timestamp("lease_expires_at"),
        optional_timestamp("recipients_resolved_at"),
        optional_timestamp("started_at"),
        optional_timestamp("finished_at"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("sent_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["kpevent.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["sent_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mailcampaign_event_id"), CAMPAIGN_TABLE, ["event_id"], unique=False
    )
    op.create_index(
        op.f("ix_mailcampaign_status"), CAMPAIGN_TABLE, ["status"], unique=False
    )
    op.create_table(
        RECIPIENT_TABLE,
        *timestamps(),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("source", sa.String(length=STATUS_LENGTH), nullable=True),
        sa.Column("contact_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=STATUS_LENGTH), nullable=False),
        sa.Column("skip_reason", sa.String(length=STATUS_LENGTH), nullable=True),
        sa.Column("error", sa.String(length=STATUS_LENGTH), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        optional_timestamp("last_attempt_at"),
        optional_timestamp("sent_at"),
        sa.ForeignKeyConstraint(["campaign_id"], [f"{CAMPAIGN_TABLE}.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["contact_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "company_id", name=RECIPIENT_UNIQUE),
    )
    op.create_index(
        op.f("ix_mailcampaignrecipient_campaign_id"),
        RECIPIENT_TABLE,
        ["campaign_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_mailcampaignrecipient_campaign_id"), table_name=RECIPIENT_TABLE
    )
    op.drop_table(RECIPIENT_TABLE)
    op.drop_index(op.f("ix_mailcampaign_status"), table_name=CAMPAIGN_TABLE)
    op.drop_index(op.f("ix_mailcampaign_event_id"), table_name=CAMPAIGN_TABLE)
    op.drop_table(CAMPAIGN_TABLE)
