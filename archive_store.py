"""Basit JSON tabanlı içerik arşivi."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

ARCHIVE_DIR = Path("archive")
ARCHIVE_FILE = ARCHIVE_DIR / "content_archive.json"


def _read() -> list[dict[str, Any]]:
    ARCHIVE_DIR.mkdir(exist_ok=True)
    if not ARCHIVE_FILE.exists():
        return []
    try:
        return json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write(items: list[dict[str, Any]]) -> None:
    ARCHIVE_DIR.mkdir(exist_ok=True)
    ARCHIVE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def add_archive(record: dict[str, Any]) -> dict[str, Any]:
    items = _read()
    record = dict(record)
    record.setdefault("created_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
    record.setdefault("status", "taslak")
    items.insert(0, record)
    _write(items[:500])
    return record


def list_archive(limit: int = 50) -> list[dict[str, Any]]:
    return _read()[:limit]


def get_archive(job_id: str) -> dict[str, Any] | None:
    for item in _read():
        if item.get("job_id") == job_id:
            return item
    return None
