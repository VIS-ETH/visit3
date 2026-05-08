import logging
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.exceptions import NotAllowed, Unauthenticated
from app.core.grpc import grpc_client
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.company_service import CompanyService
from app.services.csv_service import CsvService
from app.services.export_service import ExportService
from app.services.kp_service import KpService
from app.services.mail_service import MailService
from app.services.pdf_service import PdfService
from app.services.storage_service import StorageService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/login", refreshUrl="/users/refresh"
)

_settings = get_settings()

engine = create_async_engine(
    _settings.DATABASE_URL,
    echo=_settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_timeout=30,
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db_session():
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    try:
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
        subject = payload.get("sub")
        if subject is None:
            logger.warning("JWT decode failed - no sub claim")
            raise Unauthenticated("jwt_decode:no_sub")
    except jwt.InvalidTokenError:
        logger.warning("JWT decode failed - invalid token")
        raise Unauthenticated("jwt_decode:invalid_token")

    user_repo = UserRepository(session)
    try:
        user = await user_repo.get_by_id(UUID(subject))
    except ValueError:
        logger.warning(f"JWT decode failed - invalid subject: {subject}")
        raise Unauthenticated(f"jwt_decode:invalid_sub:{subject}")

    if user is None:
        logger.warning(f"JWT user lookup failed - user not found: {subject}")
        raise Unauthenticated(f"jwt_decode:user_not_found:{subject}")

    await user_repo.load_user_roles(user)
    logger.debug(f"User authenticated: {user.email}")

    impersonate_id = request.headers.get("X-Impersonate-User-Id")
    if impersonate_id and user.is_admin:
        try:
            target_uuid = UUID(impersonate_id)
        except ValueError:
            raise NotAllowed(f"impersonate:invalid_uuid:{impersonate_id}")
        target = await user_repo.get_by_id(target_uuid)
        if target is None:
            raise NotAllowed(f"impersonate:user_not_found:{impersonate_id}")
        await user_repo.load_user_roles(target)
        logger.info(f"Admin {user.email} impersonating: {target.email}")
        return target
    elif impersonate_id:
        raise NotAllowed(f"impersonate:not_admin:{user.email}")

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
                    "code": "csrf.validation_failed",
                    "message": "CSRF validation failed",
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


CompanyRepositoryDep = Annotated[CompanyRepository, Depends(get_company_repository)]


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
):
    return AuthService(user_repository, token_repository, role_repository, mail_service)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_company_service(
    company_repository: CompanyRepositoryDep,
    mail_service: MailServiceDep,
    current_user: CurrentUserDep,
):
    return CompanyService(company_repository, mail_service, current_user)


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]


def get_storage_service():
    return StorageService(get_settings())


StorageServiceDep = Annotated[StorageService, Depends(get_storage_service)]


async def get_kp_service(
    kp_repository: KpRepositoryDep,
    storage_service: StorageServiceDep,
    current_user: CurrentUserDep,
):
    return KpService(kp_repository, storage_service, current_user)


KpServiceDep = Annotated[KpService, Depends(get_kp_service)]


def get_pdf_service():
    return PdfService()


PdfServiceDep = Annotated[PdfService, Depends(get_pdf_service)]


def get_csv_service():
    return CsvService()


CsvServiceDep = Annotated[CsvService, Depends(get_csv_service)]


async def get_export_service(
    kp_repository: KpRepositoryDep,
    storage_service: StorageServiceDep,
    pdf_service: PdfServiceDep,
    csv_service: CsvServiceDep,
    current_user: CurrentUserDep,
):
    return ExportService(
        kp_repository, storage_service, pdf_service, csv_service, current_user
    )


ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]
