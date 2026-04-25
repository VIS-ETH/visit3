from datetime import date
from typing import Optional

from app.core.config import get_settings
from app.core.decorators import require_role
from app.core.exceptions import KpNameExists
from app.models.kp_event import KpEvent
from app.repositories.kp_repository import KpRepository


class KpService:
    def __init__(
        self,
        kp_repository: KpRepository,
    ):
        self.kp_repository = kp_repository

    async def list_kps(self) -> list[KpEvent]:
        return await self.kp_repository.list_kps()

    async def get_latest_kp(self) -> Optional[KpEvent]:
        return await self.kp_repository.get_latest_kp()

    async def get_event_by_name(self, name: str) -> Optional[KpEvent]:
        return await self.kp_repository.get_by_name(name)

    @require_role(get_settings().VISIT_KP_PRESIDENT_ROLE)
    async def create_kp(
        self,
        name: str,
        registration_open: date,
        registration_end: date,
        finalization_deadline: date,
        event_date: date,
    ) -> KpEvent:
        existing = await self.kp_repository.get_by_name(name)
        if existing is not None:
            raise KpNameExists(f"create_kp:{name}")

        return await self.kp_repository.create_kp(
            name=name,
            registration_open=registration_open,
            registration_end=registration_end,
            finalization_deadline=finalization_deadline,
            event_date=event_date,
        )
