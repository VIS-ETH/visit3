from collections.abc import Sequence
from uuid import UUID

from app.core.auth_context import require_staff_user
from app.core.exceptions import IndustryNameExists, IndustryNotFound
from app.models.industry import Industry
from app.models.user import User
from app.repositories.industry_repository import IndustryRepository


class IndustryService:
    def __init__(
        self,
        industry_repository: IndustryRepository,
        current_user: User,
    ) -> None:
        self.industry_repository = industry_repository
        self.current_user = current_user

    async def list_industries(self) -> Sequence[Industry]:
        return await self.industry_repository.list_industries()

    async def _get_industry(self, industry_id: UUID) -> Industry:
        industry = await self.industry_repository.get_by_id(industry_id)
        if industry is None:
            raise IndustryNotFound(f"industry:not_found:{industry_id}")
        return industry

    async def _ensure_name_free(
        self, name: str, current_id: UUID | None = None
    ) -> None:
        existing = await self.industry_repository.get_by_name(name)
        if existing is not None and existing.id != current_id:
            raise IndustryNameExists(f"industry:name_exists:{name}")

    async def create_industry(self, name: str) -> Industry:
        require_staff_user(self.current_user)
        normalized = name.strip()
        await self._ensure_name_free(normalized)
        return await self.industry_repository.create_industry(normalized)

    async def update_industry(self, industry_id: UUID, name: str) -> Industry:
        require_staff_user(self.current_user)
        industry = await self._get_industry(industry_id)
        normalized = name.strip()
        await self._ensure_name_free(normalized, industry.id)
        return await self.industry_repository.rename_industry(industry, normalized)

    async def delete_industry(self, industry_id: UUID) -> None:
        require_staff_user(self.current_user)
        industry = await self._get_industry(industry_id)
        await self.industry_repository.delete_industry(industry)
