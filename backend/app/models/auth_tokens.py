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
    use_count: int = Field(
        default=0, nullable=False, sa_column_kwargs={"server_default": "0"}
    )
