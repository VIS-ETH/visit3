from datetime import date
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class KpEvent(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    year: int = Field(index=True, unique=True)
    registration_open: date
    registration_end: date
    event_date: date

    def is_registration_open(self) -> bool:
        today = date.today()
        return self.registration_open <= today <= self.registration_end


class KpEventCompanyLink(SQLModel, table=True):
    event_id: UUID = Field(foreign_key="kpevent.id", primary_key=True)
    company_id: UUID = Field(foreign_key="company.id", primary_key=True)
    deleted: bool = Field(default=False)
