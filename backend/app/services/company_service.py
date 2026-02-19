from uuid import UUID
from app.core.decorators import require_admin, require_admin, require_staff
from app.core.exceptions import CompanyNotFound
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import CompanyAssignedUserResponse, CompanyWithUsersResponse


class CompanyService:
    def __init__(
        self,
        company_repository: CompanyRepository,
        current_user: User,
    ):
        self.company_repository = company_repository
        self.current_user = current_user

    @require_staff
    async def get_company_users(self, company_id: UUID) -> list[User]:
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"company_users:{company_id}")
        return await self.company_repository.get_users(company)

    @require_staff
    async def get_companies_with_users(self) -> list[CompanyWithUsersResponse]:
        companies = await self.company_repository.get_companies_with_users()
        return [
            CompanyWithUsersResponse(
                id=company.id,
                name=company.name,
                users=[
                    CompanyAssignedUserResponse(
                        id=user.id,
                        email=user.email,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        user_confirmed=user.user_confirmed,
                        email_confirmed=user.email_confirmed,
                    )
                    for user in company.users
                ],
            )
            for company in companies
        ]

    @require_admin
    async def delete_company_with_users(self, company_id: UUID):
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"delete_company_with_users:{company_id}")
        await self.company_repository.delete_company_with_users(company)
    
    @require_admin
    async def delete_company_keep_users(self, company_id: UUID):
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(f"delete_company_keep_users:{company_id}")
        await self.company_repository.delete_company_keep_users(company)
