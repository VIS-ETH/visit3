from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings

engine = create_async_engine(get_settings().DATABASE_URL, echo=True)
