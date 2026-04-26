#!/usr/bin/env python3

"""Rewrite generated protobuf imports to use the application package prefix."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def rewrite_file(path: Path, package_name: str, prefix: str) -> None:
    text = path.read_text()

    from_pattern = re.compile(rf"^from {re.escape(package_name)}(?=\.|\s)", re.MULTILINE)
    import_pattern = re.compile(rf"^import {re.escape(package_name)}(?=\.|\s)", re.MULTILINE)
    pyi_pattern = re.compile(rf"\[{re.escape(package_name)}\.")

    updated = from_pattern.sub(f"from {prefix}.{package_name}", text)
    updated = import_pattern.sub(f"import {prefix}.{package_name}", updated)

    if path.suffix == ".pyi":
        updated = pyi_pattern.sub(f"[{prefix}.{package_name}.", updated)

    if updated != text:
        path.write_text(updated)


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {Path(sys.argv[0]).name} <path> <package-prefix>")
        return 1

    target = Path(sys.argv[1])
    prefix = sys.argv[2]

    if not target.exists():
        tmp_target = Path(f"{target}-tmp")
        target.rename(tmp_target)
        target.mkdir(parents=True, exist_ok=True)
        tmp_target.rename(target)

    target = target.resolve()

    for directory in sorted(path for path in target.rglob("*") if path.is_dir()):
        package_name = ".".join(directory.relative_to(target).parts)
        if not package_name:
            continue

        print(f"{package_name} -> {prefix}.{package_name}")
        for child in directory.iterdir():
            if child.is_file() and child.suffix in {".py", ".pyi"}:
                rewrite_file(child, package_name, prefix)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
