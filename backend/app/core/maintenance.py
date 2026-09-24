from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import SessionLocal
from app.core.grpc import grpc_client, mail_stub
from app.core.scheduler import Scheduler
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.mail_repository import MailTemplateRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.booking_notifier import MailBookingNotifier
from app.services.booking_reminders import send_incomplete_booking_reminders
from app.services.invite_service import InviteService
from app.services.mail_service import MailService
from app.services.mail_template_service import MailTemplateService
from app.services.notification_recipients import NotificationRecipients
from app.services.storage_service import StorageService

HOURLY = 3600
DAILY = 86400


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


def _booking_notifier(session: AsyncSession) -> MailBookingNotifier:
    kp_repository = KpRepository(session)
    mail_template_service = MailTemplateService(
        MailTemplateRepository(session),
        NotificationRecipients(kp_repository),
        MailService(mail_stub()),
    )
    auth_service = AuthService(
        UserRepository(session),
        TokenRepository(session),
        RoleRepository(session),
        mail_template_service,
        InviteService(CompanyRepository(session)),
    )
    return MailBookingNotifier(mail_template_service, auth_service)


async def remind_incomplete_bookings() -> None:
    async with SessionLocal() as session:
        await send_incomplete_booking_reminders(
            KpRepository(session),
            _booking_notifier(session),
            datetime.now(timezone.utc),
        )


def create_scheduler() -> Scheduler:
    scheduler = Scheduler()
    scheduler.add(cleanup_expired_tokens, interval=HOURLY)
    scheduler.add(cleanup_expired_invites, interval=HOURLY)
    scheduler.add(cleanup_orphaned_stored_files, interval=HOURLY)
    scheduler.add(remind_incomplete_bookings, interval=DAILY)
    return scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    scheduler = create_scheduler()

    await grpc_client.connect(get_settings().NOTIFICATION_API_URL)
    await scheduler.start()

    yield

    await scheduler.stop()
    await grpc_client.disconnect()
