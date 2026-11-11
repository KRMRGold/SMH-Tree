"""Deterministic permission helpers for outbound model context."""
from __future__ import annotations
import json
import sqlite3
from collections.abc import Iterable, Mapping

def remote_memory_sharing_enabled(connection: sqlite3.Connection, scope: str) -> bool:
    """Return whether global or user memory may leave the device."""
    if scope not in {"global", "user"}:
        raise ValueError("Only global and user memory have remote-sharing settings.")
    row = connection.execute("SELECT value_json FROM settings WHERE key = ?", (f"share_{scope}_memory_remote",)).fetchone()
    if row is None:
        return False
    try:
        return json.loads(str(row["value_json"])) is True
    except (TypeError, ValueError):
        return False

def filter_remote_memory_items(connection: sqlite3.Connection, items: Iterable[Mapping[str, object]]) -> tuple[list[Mapping[str, object]], list[str]]:
    """Strip global/user memory by default; return retained items and dropped refs."""
    retained: list[Mapping[str, object]] = []
    dropped: list[str] = []
    for item in items:
        scope = str(item.get("scope", ""))
        if scope in {"global", "user"} and not remote_memory_sharing_enabled(connection, scope):
            dropped.append(str(item.get("id", item.get("ref", "unknown"))))
        else:
            retained.append(item)
    return retained, dropped
