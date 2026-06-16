import asyncio
from unittest.mock import AsyncMock

import pytest

from app.core.scheduler import Scheduler


@pytest.mark.asyncio
async def test_scheduler_runs_task_repeatedly():
    task = AsyncMock()
    scheduler = Scheduler()
    scheduler.add(task, interval=0)

    await scheduler.start()
    await asyncio.sleep(0.05)
    await scheduler.stop()

    assert task.await_count >= 1


@pytest.mark.asyncio
async def test_scheduler_swallows_task_exceptions():
    failing_task = AsyncMock(side_effect=RuntimeError("boom"))
    scheduler = Scheduler()
    scheduler.add(failing_task, interval=0)

    await scheduler.start()
    await asyncio.sleep(0.05)
    await scheduler.stop()

    assert failing_task.await_count >= 1


@pytest.mark.asyncio
async def test_scheduler_clears_running_tasks_on_stop():
    task = AsyncMock()
    scheduler = Scheduler()
    scheduler.add(task, interval=1)

    await scheduler.start()
    assert len(scheduler._running) == 1
    await scheduler.stop()
    assert len(scheduler._running) == 0
