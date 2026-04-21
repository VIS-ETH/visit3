from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, func

if TYPE_CHECKING:
    from app.models.user import User


class Company(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)

    users: list["User"] = Relationship(back_populates="company")
    invites: list["CompanyInvite"] = Relationship(back_populates="company")


class CompanyInvite(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token: str = Field(index=True, unique=True)
    company_id: UUID = Field(foreign_key="company.id")
    invited_email: str
    is_used: bool = Field(default=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    company: Optional["Company"] = Relationship(back_populates="invites")
