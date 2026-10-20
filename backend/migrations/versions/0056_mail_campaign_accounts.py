from typing import Sequence, Union

from alembic import op

revision: str = "0056"
down_revision: Union[str, Sequence[str], None] = "0055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "mailcampaignrecipient"
OLD_UNIQUE = "uq_mailcampaignrecipient_campaign_id_company_id"
NEW_UNIQUE = "uq_mailcampaignrecipient_campaign_company_user"


def upgrade() -> None:
    op.drop_constraint(OLD_UNIQUE, TABLE, type_="unique")
    op.create_unique_constraint(
        NEW_UNIQUE, TABLE, ["campaign_id", "company_id", "contact_user_id"]
    )


def downgrade() -> None:
    op.drop_constraint(NEW_UNIQUE, TABLE, type_="unique")
    op.create_unique_constraint(OLD_UNIQUE, TABLE, ["campaign_id", "company_id"])
