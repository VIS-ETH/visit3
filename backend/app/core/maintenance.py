import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.deps import SessionLocal
from app.core.grpc import grpc_client
from app.core.scheduler import Scheduler
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.repositories.token_repository import TokenRepository
from app.services.booklet_service import BookletService
from app.services.pdf_service import PdfService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

BOOKLET_WORKER_POLL_SECONDS = 3.0
BOOKLET_WORKER_IDLE_BACKOFF_SECONDS = 5.0


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


async def _process_pending_booklet_export_task() -> bool:
    """
    Picks one PENDING task and runs it. Returns True if a task was processed
    (caller should poll again immediately), False if the queue was empty.
    Each call uses its own DB session so the worker is independent from any
    request lifecycle.
    """
    settings = get_settings()
    async with SessionLocal() as session:
        kp_repository = KpRepository(session)
        task = await kp_repository.claim_next_pending_booklet_export_task()
        if task is None:
            return False
        storage_service = StorageService(settings)
        pdf_service = PdfService()
        # The worker runs without an authenticated user. We use a synthetic
        # admin so the BookletService's `require_staff_user` check passes.
        # No request-scoped state is touched.
        worker_user = User(
            id=task.event_id,  # placeholder UUID; only `is_admin` is read
            email="booklet-worker@internal",
            password=None,
            is_staff=True,
            is_admin=True,
            is_company=False,
            user_confirmed=True,
            email_confirmed=True,
        )
        booklet_service = BookletService(
            kp_repository, storage_service, pdf_service, worker_user
        )
        try:
            rendered = await booklet_service.render_booklet_pdf(task.event_id)
            await booklet_service.store_rendered_booklet(task, rendered)
            logger.info(
                "booklet_export_task:%s completed for event %s", task.id, task.event_id
            )
        except Exception as error:
            logger.exception(
                "booklet_export_task:%s failed for event %s", task.id, task.event_id
            )
            await kp_repository.fail_booklet_export_task(
                task, f"{type(error).__name__}:{error}"[:500]
            )
        return True


async def _run_booklet_worker(stop_event: asyncio.Event) -> None:
    async with SessionLocal() as session:
        marked = await KpRepository(
            session
        ).mark_orphan_running_booklet_export_tasks_as_failed()
    if marked > 0:
        logger.warning(
            "booklet_worker: marked %d orphaned RUNNING tasks as FAILED", marked
        )
    while not stop_event.is_set():
        try:
            processed = await _process_pending_booklet_export_task()
        except Exception:
            logger.exception("booklet_worker: unexpected error processing task")
            processed = False
        delay = (
            BOOKLET_WORKER_POLL_SECONDS
            if processed
            else BOOKLET_WORKER_IDLE_BACKOFF_SECONDS
        )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    scheduler = create_scheduler()

    await grpc_client.connect(get_settings().NOTIFICATION_API_URL)
    await scheduler.start()

    stop_event = asyncio.Event()
    booklet_worker = asyncio.create_task(_run_booklet_worker(stop_event))

    yield

    stop_event.set()
    booklet_worker.cancel()
    try:
        await booklet_worker
    except (asyncio.CancelledError, Exception):
        pass
    await scheduler.stop()
    await grpc_client.disconnect()
