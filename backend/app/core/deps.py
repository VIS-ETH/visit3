from app.services.kp_service import KpService
from app.services.company_service import CompanyService
from app.services.user_service import UserService
from app.services.mail_service import MailService
from app.services.auth_service import AuthService
from app.core.grpc import grpc_client
from typing import Annotated
import logging
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi_csrf_protect import CsrfProtect
import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, selectinload
from sqlmodel import select
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.schemas.user import TokenData
from app.core.config import get_settings
from app.core.exceptions import Unauthenticated
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/login", refreshUrl="/users/refresh"
)

engine = create_async_engine(get_settings().DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session():
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    try:
        payload = jwt.decode(
            token, get_settings().SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            logger.warning("JWT decode failed - no sub claim")
            raise Unauthenticated("jwt_decode:no_sub")
        token_data = TokenData(username=username)
    except jwt.InvalidTokenError:
        logger.warning("JWT decode failed - invalid token")
        raise Unauthenticated("jwt_decode:invalid_token")
    statement = (
        select(User)
        .where(User.email == token_data.username)
        .options(selectinload(User.roles))
    )
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(
            f"JWT user lookup failed - user not found: {token_data.username}"
        )
        raise Unauthenticated(
            f"jwt_decode:user_not_found:{token_data.username}")
    logger.debug(f"User authenticated: {user.email}")
    return user


async def get_stub():
    return grpc_client.stub


async def _csrf_dep(request: Request, csrf_protect: Annotated[CsrfProtect, Depends()]):
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        try:
            await csrf_protect.validate_csrf(request)
        except Exception:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "csrf.validation_failed",
                    "redirectTo": "/login",
                },
            )


CsrfDep = Depends(_csrf_dep)

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
MailDep = Annotated[MailServiceStub, Depends(get_stub)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_user_repository(
    session: DbSessionDep,
):
    return UserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


async def get_token_repository(
    session: DbSessionDep,
):
    return TokenRepository(session)


TokenRepositoryDep = Annotated[TokenRepository, Depends(get_token_repository)]


async def get_role_repository(
    session: DbSessionDep,
):
    return RoleRepository(session)


RoleRepositoryDep = Annotated[RoleRepository, Depends(get_role_repository)]


async def get_company_repository(
    session: DbSessionDep,
):
    return CompanyRepository(session)


CompanyRepositoryDep = Annotated[CompanyRepository, Depends(
    get_company_repository)]


async def get_kp_repository(
    session: DbSessionDep,
):
    return KpRepository(session)


KpRepositoryDep = Annotated[KpRepository, Depends(get_kp_repository)]


async def get_mail_service(mail: MailDep):
    return MailService(mail)


MailServiceDep = Annotated[MailService, Depends(get_mail_service)]


async def get_user_service(
    user_repository: UserRepositoryDep,
    token_repository: TokenRepositoryDep,
    mail_service: MailServiceDep,
    current_user: CurrentUserDep,
):
    return UserService(user_repository, token_repository, mail_service, current_user)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_auth_service(
    user_repository: UserRepositoryDep,
    token_repository: TokenRepositoryDep,
    role_repository: RoleRepositoryDep,
    mail_service: MailServiceDep,
    company_repository: CompanyRepositoryDep,
):
    return AuthService(
        user_repository, token_repository, role_repository, mail_service, company_repository
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_company_service(
    company_repository: CompanyRepositoryDep,
    current_user: CurrentUserDep,
):
    return CompanyService(company_repository, current_user)


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]


async def get_kp_service(
    kp_repository: KpRepositoryDep,
    company_repository: CompanyRepositoryDep,
    current_user: CurrentUserDep,
):
    return KpService(kp_repository, company_repository, current_user)


KpServiceDep = Annotated[KpService, Depends(get_kp_service)]
