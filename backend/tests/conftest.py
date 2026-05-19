import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def _load_test_env_defaults() -> None:
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


_load_test_env_defaults()
os.environ["DEBUG"] = "false"
