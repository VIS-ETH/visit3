from typing import TYPE_CHECKING
from sqlmodel import Relationship, SQLModel, Field
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from app.models.user import User


class Company(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)

    users: list["User"] = Relationship(back_populates="company")
