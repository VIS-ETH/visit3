import os
import time
from pathlib import Path

from app.services.pdf_service import PdfUnreadable


def echo(value: object) -> object:
    return value


def sleep_after_writing_pid(seconds: float, pid_file: str) -> str:
    Path(pid_file).write_text(str(os.getpid()))
    time.sleep(seconds)
    return "finished"


def process_id() -> int:
    return os.getpid()


def fail_as_unreadable() -> None:
    raise PdfUnreadable("broken pdf")


def exit_abruptly() -> None:
    os._exit(9)
