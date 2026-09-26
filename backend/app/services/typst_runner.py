import asyncio
import multiprocessing
import pickle
import queue
import resource
import time
from collections.abc import Callable
from functools import lru_cache
from multiprocessing.connection import Connection
from multiprocessing.context import ForkServerContext
from typing import Any, cast

from app.core.config import get_settings

WORKER_MODULES = ["typst", "app.services.typst_worker"]
MEGABYTE = 1024 * 1024
JOIN_GRACE_SECONDS = 1
MAX_JOBS_PER_WORKER = 200


class TypstRenderAborted(Exception):
    pass


def _portable(error: Exception) -> Exception:
    try:
        pickle.loads(pickle.dumps(error))
    except Exception:
        return RuntimeError(str(error))
    return error


def _serve(connection: Connection, memory_limit_bytes: int | None) -> None:
    if memory_limit_bytes is not None:
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
    while True:
        try:
            function, arguments = connection.recv()
        except EOFError:
            return
        try:
            outcome: tuple[bool, Any] = (True, function(*arguments))
        except Exception as error:
            outcome = (False, _portable(error))
        connection.send(outcome)


class _Worker:
    def __init__(
        self, context: ForkServerContext, memory_limit_bytes: int | None
    ) -> None:
        self.connection, worker_end = context.Pipe()
        self.process = context.Process(
            target=_serve, args=(worker_end, memory_limit_bytes), daemon=True
        )
        self.process.start()
        worker_end.close()
        self.jobs = 0

    def stop(self) -> None:
        self.connection.close()
        if self.process.is_alive():
            self.process.kill()
        self.process.join(JOIN_GRACE_SECONDS)


class TypstRunner:
    def __init__(
        self,
        max_parallel: int,
        memory_limit_bytes: int | None,
        max_jobs_per_worker: int = MAX_JOBS_PER_WORKER,
    ) -> None:
        self.memory_limit_bytes = memory_limit_bytes
        self.max_jobs_per_worker = max_jobs_per_worker
        self._context = multiprocessing.get_context("forkserver")
        self._context.set_forkserver_preload(WORKER_MODULES)
        self._slots: queue.Queue[_Worker | None] = queue.Queue()
        for _ in range(max_parallel):
            self._slots.put(None)

    async def run(
        self,
        function: Callable[..., Any],
        arguments: tuple[Any, ...],
        timeout: float,
    ) -> Any:
        return await asyncio.to_thread(self._run, function, arguments, timeout)

    def _run(
        self,
        function: Callable[..., Any],
        arguments: tuple[Any, ...],
        timeout: float,
    ) -> Any:
        deadline = time.monotonic() + timeout
        try:
            worker = self._slots.get(timeout=timeout)
        except queue.Empty:
            raise TypstRenderAborted("busy") from None
        reusable = False
        try:
            if worker is None or not worker.process.is_alive():
                worker = _Worker(self._context, self.memory_limit_bytes)
            succeeded, value = self._exchange(worker, function, arguments, deadline)
            worker.jobs += 1
            reusable = worker.jobs < self.max_jobs_per_worker
        finally:
            if worker is not None and not reusable:
                worker.stop()
            self._slots.put(worker if reusable else None)
        if not succeeded:
            raise cast(Exception, value)
        return value

    def _exchange(
        self,
        worker: _Worker,
        function: Callable[..., Any],
        arguments: tuple[Any, ...],
        deadline: float,
    ) -> tuple[bool, Any]:
        try:
            worker.connection.send((function, arguments))
        except OSError:
            raise TypstRenderAborted("crashed") from None
        if not worker.connection.poll(max(deadline - time.monotonic(), 0)):
            raise TypstRenderAborted("timeout")
        try:
            return cast(tuple[bool, Any], worker.connection.recv())
        except EOFError:
            raise TypstRenderAborted("crashed") from None


@lru_cache
def typst_runner() -> TypstRunner:
    settings = get_settings()
    return TypstRunner(
        max_parallel=settings.TYPST_MAX_PARALLEL_RENDERS,
        memory_limit_bytes=settings.TYPST_RENDER_MEMORY_LIMIT_MB * MEGABYTE,
    )
