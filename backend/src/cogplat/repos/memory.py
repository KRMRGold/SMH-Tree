"""Persistence operations for memory items."""
from __future__ import annotations
import sqlite3
from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now

def get_memory_item(connection: sqlite3.Connection, memory_id: str) -> dict[str, object] | None:
    row = connection.execute(
        "SELECT id, scope, scope_id, kind, content, importance, state, superseded_by, "
        "origin_kind, origin_ref, created_at, updated_at FROM memory_items WHERE id = ?",
        (memory_id,),
    ).fetchone()
    return dict(row) if row is not None else None

def insert_memory_item(connection: sqlite3.Connection, *, scope: str, scope_id: str | None,
                       kind: str, content: str, importance: int, origin_kind: str,
                       origin_ref: str | None) -> dict[str, object]:
    memory_id = new_id()
    now = utc_now()
    connection.execute(
        "INSERT INTO memory_items "
        "(id, scope, scope_id, kind, content, importance, state, superseded_by, "
        "origin_kind, origin_ref, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'active', NULL, ?, ?, ?, ?)",
        (memory_id, scope, scope_id, kind, content, importance, origin_kind, origin_ref, now, now),
    )
    return get_memory_item(connection, memory_id)

def set_memory_state(connection: sqlite3.Connection, memory_id: str, state: str,
                     superseded_by: str | None) -> dict[str, object] | None:
    connection.execute(
        "UPDATE memory_items SET state = ?, superseded_by = ?, updated_at = ? WHERE id = ?",
        (state, superseded_by, utc_now(), memory_id),
    )
    return get_memory_item(connection, memory_id)
