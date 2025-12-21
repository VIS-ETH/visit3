from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy import Engine
from sqlmodel import Session, create_engine, select
from app.config import Settings
from app.models.user import User
from app.schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

def get_settings():
    settings = Settings()
    return settings

SettingsDep = Annotated[Settings, Depends(get_settings)]

def get_engine(settings: Annotated[Settings, Depends(get_settings)]):
    engine = create_engine(settings.DATABASE_URL, connect_args={})
    return engine

EngineDep = Annotated[Engine, Depends(get_engine)]


def get_db_session(engine: Annotated[Engine, Depends(get_engine)]):
    with Session(engine) as session:
        yield session
        
DbSessionDep = Annotated[Session, Depends(get_db_session)]
        
        
async def get_current_user(settings: SettingsDep, session: DbSessionDep, token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.InvalidTokenError:
        raise credentials_exception
    statement = select(User).where(User.username == token_data.username)
    user = session.exec(statement).first()
    if user is None:
        raise credentials_exception
    return user

CurrentUserDep = Annotated[User, Depends(get_current_user)]
        
