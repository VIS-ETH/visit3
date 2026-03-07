from datetime import date
from typing import Optional

from app.core.decorators import require_staff
from app.models.kp_event import KpEvent
from app.models.user import User
from app.repositories.kp_repository import KpRepository


class KpService:
    def __init__(
        self,
        kp_repository: KpRepository,
        current_user: User,
    ):
        self.kp_repository = kp_repository
        self.current_user = current_user

    async def get_events(self) -> list[KpEvent]:
        return await self.kp_repository.list_events()

    async def get_latest_event(self) -> Optional[KpEvent]:
        return await self.kp_repository.get_latest_event()

    async def get_event_by_year(self, year: int) -> Optional[KpEvent]:
        return await self.kp_repository.get_by_year(year)

    @require_staff
    async def create_event(
        self,
        year: int,
        registration_open: date,
        registration_end: date,
        event_date: date,
    ) -> KpEvent:
        return await self.kp_repository.create_event(
            year=year,
            registration_open=registration_open,
            registration_end=registration_end,
            event_date=event_date,
        )
