from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.deleted_filter import hide_deleted_rows_in_orm_queries

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

hide_deleted_rows_in_orm_queries()


async def get_db_session():
    async with SessionLocal() as session:
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
