from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.deps import SessionLocal
from app.core.grpc import grpc_client
from app.core.scheduler import Scheduler
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.token_repository import TokenRepository
from app.services.storage_service import StorageService


async def cleanup_expired_tokens() -> None:
    async with SessionLocal() as session:
        await TokenRepository(session).cleanup_expired()


async def cleanup_expired_invites() -> None:
    async with SessionLocal() as session:
        await CompanyRepository(session).cleanup_expired_invites()


async def cleanup_orphaned_stored_files() -> None:
    async with SessionLocal() as session:
        settings = get_settings()
        storage_service = StorageService(settings)
        kp_repository = KpRepository(session)
        orphaned_files = await kp_repository.list_orphaned_stored_files(
            settings.STORAGE_ORPHAN_CLEANUP_MAX_AGE_HOURS
        )
        for stored_file in orphaned_files:
            await storage_service.delete_object(stored_file.storage_key)
            await kp_repository.delete_stored_file(stored_file)


def create_scheduler() -> Scheduler:
    scheduler = Scheduler()
    scheduler.add(cleanup_expired_tokens, interval=3600)
    scheduler.add(cleanup_expired_invites, interval=3600)
    scheduler.add(cleanup_orphaned_stored_files, interval=3600)
    return scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    scheduler = create_scheduler()

    await grpc_client.connect(get_settings().NOTIFICATION_API_URL)
    await scheduler.start()

    yield

    await scheduler.stop()
    await grpc_client.disconnect()
