from datetime import datetime
import uuid
from sqlmodel import Column, DateTime, SQLModel, Field, func


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    email: str = Field(unique=True, index=True)
    sub: str | None = Field(default=None, index=True)
    password: str | None
    first_name: str | None = None
    last_name: str | None = None

    is_confirmed: bool = False
    is_staff: bool = False
    is_admin: bool = False


class RefreshToken(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True, nullable=False
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    token: str = Field(index=True, unique=True)

    is_revoked: bool = Field(default=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
