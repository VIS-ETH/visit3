from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, SQLModel  # pyright: ignore[reportUnknownVariableType]

TIMESTAMPTZ = cast(type[Any], TIMESTAMP(timezone=True))


class AppBase(SQLModel):
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=TIMESTAMPTZ,
        sa_column_kwargs={"server_default": func.now()},
    )
    deleted_at: datetime | None = Field(
        default=None,
        nullable=True,
        sa_type=TIMESTAMPTZ,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def mark_deleted(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)


class BaseEntity(AppBase):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=TIMESTAMPTZ,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


class BaseLink(AppBase):
    pass


class BaseToken(BaseEntity):
    user_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    token: str = Field(index=True, unique=True)
    is_revoked: bool = Field(default=False)
    expires_at: datetime = Field(
        ...,
        nullable=False,
        sa_type=TIMESTAMPTZ,
        index=True,
    )
