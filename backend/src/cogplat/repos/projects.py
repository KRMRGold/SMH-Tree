"""Project persistence operations."""

from __future__ import annotations

import sqlite3

from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now


def create_project(
    connection: sqlite3.Connection, name: str, description: str | None
) -> dict[str, object]:
    project_id = new_id()
    created_at = utc_now()
    connection.execute(
        "INSERT INTO projects(id, name, description, created_at) VALUES (?, ?, ?, ?)",
        (project_id, name, description, created_at),
    )
    return get_project(connection, project_id)


def get_project(connection: sqlite3.Connection, project_id: str) -> dict[str, object] | None:
    row = connection.execute(
        "SELECT id, name, description, created_at, archived_at FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def list_projects(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        "SELECT id, name, description, created_at, archived_at "
        "FROM projects WHERE archived_at IS NULL ORDER BY created_at, id"
    ).fetchall()
    return [dict(row) for row in rows]
