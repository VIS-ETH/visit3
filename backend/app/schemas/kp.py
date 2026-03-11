from datetime import date

from pydantic import BaseModel


class CreateKpRequest(BaseModel):
    year: int
    registration_open: date
    registration_end: date
    event_date: date
