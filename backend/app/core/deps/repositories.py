from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps.database import DbSessionDep
from app.repositories.change_repository import ChangeRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.industry_repository import IndustryRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.mail_campaign_repository import MailCampaignRepository
from app.repositories.mail_repository import MailTemplateRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.venue_repository import VenueRepository


def _repository[R](
    repository: Callable[[AsyncSession], R],
) -> Callable[[AsyncSession], Awaitable[R]]:
    async def get_repository(session: DbSessionDep) -> R:
        return repository(session)

    return get_repository


ChangeRepositoryDep = Annotated[
    ChangeRepository, Depends(_repository(ChangeRepository))
]
CompanyRepositoryDep = Annotated[
    CompanyRepository, Depends(_repository(CompanyRepository))
]
IndustryRepositoryDep = Annotated[
    IndustryRepository, Depends(_repository(IndustryRepository))
]
KpRepositoryDep = Annotated[KpRepository, Depends(_repository(KpRepository))]
MailCampaignRepositoryDep = Annotated[
    MailCampaignRepository, Depends(_repository(MailCampaignRepository))
]
MailTemplateRepositoryDep = Annotated[
    MailTemplateRepository, Depends(_repository(MailTemplateRepository))
]
RoleRepositoryDep = Annotated[RoleRepository, Depends(_repository(RoleRepository))]
TokenRepositoryDep = Annotated[TokenRepository, Depends(_repository(TokenRepository))]
UserRepositoryDep = Annotated[UserRepository, Depends(_repository(UserRepository))]
VenueRepositoryDep = Annotated[VenueRepository, Depends(_repository(VenueRepository))]
