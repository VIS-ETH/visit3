import asyncio
from unittest.mock import AsyncMock, MagicMock, NonCallableMock, patch
from uuid import uuid4

import pytest

from app.core import maintenance
from app.core.maintenance import (
    _process_pending_booklet_export_task,
    _run_booklet_worker,
    cleanup_expired_invites,
    cleanup_expired_tokens,
    cleanup_orphaned_stored_files,
    create_scheduler,
)
from app.models.kp_event import KpEventBookletExportTask


@patch.object(maintenance.TokenRepository, "cleanup_expired")
@patch.object(maintenance, "SessionLocal")
@pytest.mark.asyncio
async def test_cleanup_expired_tokens_calls_repository(
    mock_session_local, mock_cleanup_expired
):
    session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = session

    await cleanup_expired_tokens()

    mock_session_local.assert_called_once()
    mock_cleanup_expired.assert_awaited_once()


@patch.object(maintenance.CompanyRepository, "cleanup_expired_invites")
@patch.object(maintenance, "SessionLocal")
@pytest.mark.asyncio
async def test_cleanup_expired_invites_calls_repository(
    mock_session_local, mock_cleanup_expired_invites
):
    session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = session

    await cleanup_expired_invites()

    mock_session_local.assert_called_once()
    mock_cleanup_expired_invites.assert_awaited_once()


@patch.object(maintenance, "SessionLocal")
@patch.object(maintenance, "StorageService")
@patch.object(maintenance, "KpRepository")
@patch.object(maintenance, "get_settings")
@pytest.mark.asyncio
async def test_cleanup_orphaned_stored_files_deletes_files(
    mock_get_settings,
    mock_kp_repository_cls,
    mock_storage_service_cls,
    mock_session_local,
):
    settings = MagicMock()
    settings.STORAGE_ORPHAN_CLEANUP_MAX_AGE_HOURS = 24
    mock_get_settings.return_value = settings

    session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = session

    stored_file = MagicMock()
    stored_file.storage_key = "orphan-key"
    kp_repo = AsyncMock()
    kp_repo.list_orphaned_stored_files.return_value = [stored_file]
    mock_kp_repository_cls.return_value = kp_repo

    storage_service = AsyncMock()
    mock_storage_service_cls.return_value = storage_service

    await cleanup_orphaned_stored_files()

    storage_service.delete_object.assert_awaited_once_with("orphan-key")
    kp_repo.delete_stored_file.assert_awaited_once_with(stored_file)


def test_create_scheduler_registers_three_tasks():
    scheduler = create_scheduler()

    assert len(scheduler._tasks) == 3
    task_names = {task.__name__ for task, _ in scheduler._tasks}
    assert task_names == {
        "cleanup_expired_tokens",
        "cleanup_expired_invites",
        "cleanup_orphaned_stored_files",
    }
    assert all(interval == 3600 for _, interval in scheduler._tasks)


@patch.object(maintenance, "SessionLocal")
@patch.object(maintenance, "BookletService")
@patch.object(maintenance, "PdfService")
@patch.object(maintenance, "StorageService")
@patch.object(maintenance, "KpRepository")
@patch.object(maintenance, "get_settings")
@pytest.mark.asyncio
async def test_process_pending_booklet_export_task_completes_task(
    mock_get_settings,
    mock_kp_repository_cls,
    mock_storage_service_cls,
    mock_pdf_service_cls,
    mock_booklet_service_cls,
    mock_session_local,
):
    session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = session

    task = MagicMock(spec=KpEventBookletExportTask)
    task.id = uuid4()
    task.event_id = uuid4()
    kp_repo = AsyncMock()
    kp_repo.claim_next_pending_booklet_export_task.return_value = task
    mock_kp_repository_cls.return_value = kp_repo

    rendered = MagicMock()
    rendered.content = b"pdf-content"
    rendered.filename = "booklet.pdf"
    booklet_service = AsyncMock()
    booklet_service.render_booklet_pdf.return_value = rendered
    mock_booklet_service_cls.return_value = booklet_service

    result = await _process_pending_booklet_export_task()

    assert result is True
    booklet_service.render_booklet_pdf.assert_awaited_once_with(task.event_id)
    booklet_service.store_rendered_booklet.assert_awaited_once_with(task, rendered)
    kp_repo.fail_booklet_export_task.assert_not_awaited()


@patch.object(maintenance, "SessionLocal")
@patch.object(maintenance, "BookletService")
@patch.object(maintenance, "PdfService")
@patch.object(maintenance, "StorageService")
@patch.object(maintenance, "KpRepository")
@patch.object(maintenance, "get_settings")
@pytest.mark.asyncio
async def test_process_pending_booklet_export_task_handles_render_failure(
    mock_get_settings,
    mock_kp_repository_cls,
    mock_storage_service_cls,
    mock_pdf_service_cls,
    mock_booklet_service_cls,
    mock_session_local,
):
    session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = session

    task = MagicMock(spec=KpEventBookletExportTask)
    task.id = uuid4()
    task.event_id = uuid4()
    kp_repo = AsyncMock()
    kp_repo.claim_next_pending_booklet_export_task.return_value = task
    mock_kp_repository_cls.return_value = kp_repo

    booklet_service = AsyncMock()
    booklet_service.render_booklet_pdf.side_effect = RuntimeError("render failed")
    mock_booklet_service_cls.return_value = booklet_service

    result = await _process_pending_booklet_export_task()

    assert result is True
    kp_repo.fail_booklet_export_task.assert_awaited_once()


def _make_session_mock():
    session = AsyncMock()
    execute_result = NonCallableMock()
    scalars_result = NonCallableMock()
    scalars_result.all.return_value = []
    execute_result.scalars.return_value = scalars_result
    session.execute.return_value = execute_result
    return session


@patch.object(maintenance, "BOOKLET_WORKER_POLL_SECONDS", 0.05)
@patch.object(maintenance, "SessionLocal")
@patch.object(maintenance, "_process_pending_booklet_export_task")
@pytest.mark.asyncio
async def test_run_booklet_worker_polls_fast_when_task_processed(
    mock_process_task, mock_session_local
):
    session = _make_session_mock()
    mock_session_local.return_value.__aenter__.return_value = session
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_process_task.return_value = True

    stop_event = asyncio.Event()

    async def stop_soon():
        await asyncio.sleep(0.15)
        stop_event.set()

    await asyncio.gather(
        _run_booklet_worker(stop_event),
        stop_soon(),
    )

    assert mock_process_task.await_count >= 1


@patch.object(maintenance, "BOOKLET_WORKER_IDLE_BACKOFF_SECONDS", 0.05)
@patch.object(maintenance, "SessionLocal")
@patch.object(maintenance, "_process_pending_booklet_export_task")
@pytest.mark.asyncio
async def test_run_booklet_worker_polls_slow_when_queue_empty(
    mock_process_task, mock_session_local
):
    session = _make_session_mock()
    mock_session_local.return_value.__aenter__.return_value = session
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_process_task.return_value = False

    stop_event = asyncio.Event()

    async def stop_soon():
        await asyncio.sleep(0.15)
        stop_event.set()

    await asyncio.gather(
        _run_booklet_worker(stop_event),
        stop_soon(),
    )

    assert mock_process_task.await_count >= 1
