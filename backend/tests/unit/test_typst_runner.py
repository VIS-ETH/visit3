import asyncio
import os
import time
from pathlib import Path

import pytest

from app.services.pdf_service import PdfUnreadable
from app.services.typst_runner import TypstRenderAborted, TypstRunner
from tests.unit import typst_work


def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def test_a_render_returns_the_result_of_the_worker():
    runner = TypstRunner(max_parallel=2, memory_limit_bytes=None)

    assert await runner.run(typst_work.echo, ({"page": b"png"},), timeout=10) == {
        "page": b"png"
    }


async def test_a_render_over_the_limit_is_aborted_and_its_worker_killed(
    tmp_path: Path,
):
    runner = TypstRunner(max_parallel=1, memory_limit_bytes=None)
    await runner.run(typst_work.process_id, (), timeout=10)
    pid_file = tmp_path / "pid"
    started = time.monotonic()

    with pytest.raises(TypstRenderAborted):
        await runner.run(
            typst_work.sleep_after_writing_pid, (30, str(pid_file)), timeout=1
        )

    assert time.monotonic() - started < 5
    assert not is_running(int(pid_file.read_text()))


async def test_a_worker_is_reused_between_renders():
    runner = TypstRunner(max_parallel=1, memory_limit_bytes=None)

    first = await runner.run(typst_work.process_id, (), timeout=10)
    second = await runner.run(typst_work.process_id, (), timeout=10)

    assert first == second


async def test_a_fresh_worker_takes_over_after_a_killed_one(tmp_path: Path):
    runner = TypstRunner(max_parallel=1, memory_limit_bytes=None)
    await runner.run(typst_work.process_id, (), timeout=10)
    with pytest.raises(TypstRenderAborted):
        await runner.run(
            typst_work.sleep_after_writing_pid, (30, str(tmp_path / "pid")), timeout=1
        )

    replacement = await runner.run(typst_work.process_id, (), timeout=10)

    assert replacement != int((tmp_path / "pid").read_text())
    assert is_running(replacement)


async def test_a_worker_is_replaced_after_its_job_budget():
    runner = TypstRunner(max_parallel=1, memory_limit_bytes=None, max_jobs_per_worker=1)

    first = await runner.run(typst_work.process_id, (), timeout=10)
    second = await runner.run(typst_work.process_id, (), timeout=10)

    assert first != second
    assert not is_running(first)


async def test_the_error_of_a_worker_reaches_the_caller():
    runner = TypstRunner(max_parallel=2, memory_limit_bytes=None)

    with pytest.raises(PdfUnreadable):
        await runner.run(typst_work.fail_as_unreadable, (), timeout=10)


async def test_a_crashed_worker_aborts_the_render():
    runner = TypstRunner(max_parallel=2, memory_limit_bytes=None)

    with pytest.raises(TypstRenderAborted):
        await runner.run(typst_work.exit_abruptly, (), timeout=10)


async def test_waiting_for_a_free_slot_counts_towards_the_limit(tmp_path: Path):
    runner = TypstRunner(max_parallel=1, memory_limit_bytes=None)
    busy = asyncio.create_task(
        runner.run(
            typst_work.sleep_after_writing_pid,
            (2, str(tmp_path / "busy")),
            timeout=10,
        )
    )
    await asyncio.sleep(0.5)
    started = time.monotonic()

    with pytest.raises(TypstRenderAborted):
        await runner.run(typst_work.echo, ("late",), timeout=0.5)

    assert time.monotonic() - started < 1.5
    assert await busy == "finished"
