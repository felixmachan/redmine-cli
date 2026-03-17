from __future__ import annotations

import os
from pathlib import Path


WORKSPACE_MARKERS = (".env", "main.py", "unfilled.xlsx")


def discover_workspace_root(start: Path | None = None) -> Path:
    env_override = os.getenv("REDMINE_TIMETABLE_WORKDIR", "").strip()
    package_root = os.getenv("REDMINE_TIMETABLE_PACKAGE_ROOT", "").strip()
    current = Path(env_override or start or Path.cwd()).resolve()

    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in WORKSPACE_MARKERS):
            return candidate

    if package_root:
        fallback = Path(package_root).resolve()
        if fallback.exists():
            return fallback

    return current


def resolve_workspace_path(workspace_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return workspace_root / path


def discover_current_dir() -> Path:
    current_dir = os.getenv("REDMINE_TIMETABLE_CURRENT_DIR", "").strip()
    return Path(current_dir or Path.cwd()).resolve()
