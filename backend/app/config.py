from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    GRPC_SERVER: str
    FRONTEND_SERVER: str


@lru_cache
def get_settings():
    return Settings()
