from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from app.db import engine
from app.models.user import User
from app.schemas.user import TokenData
from app.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


async def get_db_session():
    session_fac = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_fac() as session:
        yield session
        
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
 
async def get_current_user(session: DbSessionDep, token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.InvalidTokenError:
        raise credentials_exception
    statement = select(User).where(User.email == token_data.username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

CurrentUserDep = Annotated[User, Depends(get_current_user)]
        
