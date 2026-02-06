from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import grpc
import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from app.models.user import User
from app.schemas.user import TokenData
from app.config import get_settings
from app.utils.exceptions import unauth_e, not_allowed_e
from app.generated.sip.notifications.mail_pb2_grpc import MailServiceStub

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/login", refreshUrl="/users/refresh"
)


class GRPCClient:
    def __init__(self):
        self.channel = None
        self.stub = None

    async def connect(self, target: str):
        self.channel = grpc.aio.insecure_channel(target)
        self.stub = MailServiceStub(self.channel)

    async def disconnect(self):
        if self.channel:
            await self.channel.close()


engine = create_async_engine(get_settings().DATABASE_URL, echo=True)
grpc_client = GRPCClient()


async def get_db_session():
    session_fac = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_fac() as session:
        yield session


async def get_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    try:
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise unauth_e
        token_data = TokenData(username=username)
    except jwt.InvalidTokenError:
        raise unauth_e
    statement = select(User).where(User.email == token_data.username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    if user is None:
        raise unauth_e
    return user


async def get_stub():
    return grpc_client.stub


class _Context:
    def __init__(
        self,
        session: Annotated[AsyncSession, Depends(get_db_session)],
        mail_stub: Annotated[MailServiceStub, Depends(get_stub)],
    ):
        self.session = session
        self.mail_stub = mail_stub


class _UserContext(_Context):
    def __init__(
        self,
        session: Annotated[AsyncSession, Depends(get_db_session)],
        mail_stub: Annotated[MailServiceStub, Depends(get_stub)],
        user: Annotated[User, Depends(get_user)],
    ):
        super().__init__(session, mail_stub)
        self.user = user

    def verify_staff(self):
        if not self.user.is_staff:
            raise not_allowed_e

    def verify_admin(self):
        if not self.user.is_admin:
            raise not_allowed_e


Context = Annotated[_Context, Depends()]
UserContext = Annotated[_UserContext, Depends()]
