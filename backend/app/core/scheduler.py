import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self):
        self._tasks: list[tuple[Callable[[], Coroutine[Any, Any, None]], int]] = []
        self._running: list[asyncio.Task] = []

    def add(self, func: Callable[[], Coroutine[Any, Any, None]], interval: int):
        self._tasks.append((func, interval))

    async def start(self):
        for func, interval in self._tasks:
            self._running.append(asyncio.create_task(self._loop(func, interval)))

    async def stop(self):
        for task in self._running:
            task.cancel()
        self._running.clear()

    async def _loop(self, func: Callable[[], Coroutine[Any, Any, None]], interval: int):
        while True:
            await asyncio.sleep(interval)
            try:
                await func()
            except Exception:
                logger.exception(f"Scheduled task {func.__name__} failed")
