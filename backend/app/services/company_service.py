from uuid import UUID
import logging
from app.core.decorators import require_admin, require_confirmed_company, require_staff
from app.core.exceptions import CompanyNotFound, NotAllowed
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import CompanyAssignedUserResponse, CompanyWithUsersResponse

logger = logging.getLogger(__name__)


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
                        phone_number=user.phone_number,
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

    @require_confirmed_company
    async def update_company_name(self, name: str):
        if not self.current_user.company_id:
            logger.warning(
                f"Update company name failed - user has no company: {self.current_user.email}"
            )
            raise NotAllowed(f"update_company_name:{self.current_user.id}")

        company = await self.company_repository.get_by_id(self.current_user.company_id)
        if not company:
            logger.warning(
                f"Update company name failed - company not found: {self.current_user.company_id}"
            )
            raise CompanyNotFound(f"update_company_name:{self.current_user.company_id}")

        updated_company = await self.company_repository.update_company_name(
            company, name
        )
        logger.info(
            f"Company name updated by {self.current_user.email}: {company.name} -> {name}"
        )
        return updated_company
