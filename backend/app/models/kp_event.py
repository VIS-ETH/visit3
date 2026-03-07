from datetime import date
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class KpEvent(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    year: int = Field(index=True, unique=True)
    registration_open: date
    registration_end: date
    event_date: date
