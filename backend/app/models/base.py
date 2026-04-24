from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class AppBase(SQLModel):
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )
    )
    deleted_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True), default=None
    )


class BaseEntity(AppBase):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )
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
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
