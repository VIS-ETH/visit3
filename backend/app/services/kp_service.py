from datetime import date
from typing import Optional
from uuid import UUID

from app.core.config import get_settings
from app.core.decorators import require_confirmed_company, require_role
from app.core.exceptions import KpYearExists
from app.models.company import Company
from app.models.kp_event import KpEvent
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository


class KpService:
    def __init__(
        self,
        kp_repository: KpRepository,
        company_repository: CompanyRepository,
        current_user: User,
    ):
        self.kp_repository = kp_repository
        self.company_repository = company_repository
        self.current_user = current_user

    async def list_kps(self) -> list[KpEvent]:
        return await self.kp_repository.list_kps()

    async def get_latest_kp(self) -> Optional[KpEvent]:
        return await self.kp_repository.get_latest_kp()

    async def get_event_by_year(self, year: int) -> Optional[KpEvent]:
        return await self.kp_repository.get_by_year(year)

    @require_role(get_settings().VISIT_KP_PRESIDENT_ROLE)
    async def create_kp(
        self,
        year: int,
        registration_open: date,
        registration_end: date,
        event_date: date,
    ) -> KpEvent:
        existing = await self.kp_repository.get_by_year(year)
        if existing is not None:
            raise KpYearExists(f"create_kp:{year}")

        return await self.kp_repository.create_kp(
            year=year,
            registration_open=registration_open,
            registration_end=registration_end,
            event_date=event_date,
        )

    @require_confirmed_company
    async def register_company_for_kp(self, event_id: UUID):
        kp = await self.kp_repository.get_by_id(event_id)
        if kp is None:
            raise ValueError(f"KpEvent with id {event_id} not found")
        if not kp.is_registration_open():
            raise ValueError(f"Registration for KpEvent with id {event_id} is not open")
        await self.kp_repository.register_company_for_kp(
            company_id=self.current_user.company_id, event_id=event_id
        )

    @require_confirmed_company
    async def deregister_company_from_kp(self, event_id: UUID):
        kp = await self.kp_repository.get_by_id(event_id)
        if kp is None:
            raise ValueError(f"KpEvent with id {event_id} not found")
        await self.kp_repository.deregister_company_from_kp(
            company_id=self.current_user.company_id, event_id=event_id
        )

    async def get_companies_for_kp(self, event_id: UUID) -> list[Company]:
        kp = await self.kp_repository.get_by_id(event_id)
        if kp is None:
            raise ValueError(f"KpEvent with id {event_id} not found")
        companies = await self.kp_repository.list_companies_for_kp(event_id)
        return await self.company_repository.get_by_ids(companies)
