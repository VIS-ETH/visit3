from datetime import datetime

from sqlmodel import Field

from app.models.base import TIMESTAMPTZ, BaseToken


class LoginLinkToken(BaseToken, table=True):
    target_path: str = Field(default="/")
    used_at: datetime | None = Field(
        default=None,
        nullable=True,
        sa_type=TIMESTAMPTZ,
    )
