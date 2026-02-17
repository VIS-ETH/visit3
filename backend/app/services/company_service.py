from uuid import UUID
from app.core.exceptions import CompanyNotFound
from app.models.company import Company
from app.models.user import User
from app.repositories.company_repository import CompanyRepository


class CompanyService:
    def __init__(
        self,
        company_repository: CompanyRepository,
        current_user: User,
    ):
        self.company_repository = company_repository
        self.current_user = current_user

    async def get_company_users(self, company_id: UUID) -> list[User]:
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"company_users:{company_id}")
        return await self.company_repository.get_users(company)
