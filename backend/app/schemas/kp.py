from datetime import date

from pydantic import BaseModel


class CreateKpRequest(BaseModel):
    name: str
    registration_open: date
    registration_end: date
    finalization_deadline: date
    event_date: date
