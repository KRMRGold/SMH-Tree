"""Conversation, branch, and message persistence operations."""

from __future__ import annotations

import sqlite3

from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now


def get_conversation(
    connection: sqlite3.Connection, conversation_id: str
) -> dict[str, object] | None:
    row = connection.execute(
        "SELECT id, project_id, title, root_branch_id, created_at, archived_at "
        "FROM conversations WHERE id = ?",
        (conversation_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def list_conversations(
    connection: sqlite3.Connection, project_id: str | None = None
) -> list[dict[str, object]]:
    if project_id is None:
        rows = connection.execute(
            "SELECT id, project_id, title, root_branch_id, created_at, archived_at "
            "FROM conversations WHERE archived_at IS NULL ORDER BY created_at, id"
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT id, project_id, title, root_branch_id, created_at, archived_at "
            "FROM conversations WHERE archived_at IS NULL AND project_id = ? "
            "ORDER BY created_at, id",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_branch(connection: sqlite3.Connection, branch_id: str) -> dict[str, object] | None:
    row = connection.execute(
        "SELECT id, conversation_id, parent_branch_id, fork_message_id, name, created_at "
        "FROM branches WHERE id = ?",
        (branch_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def list_branches(
    connection: sqlite3.Connection, conversation_id: str
) -> list[dict[str, object]]:
    rows = connection.execute(
        "SELECT id, conversation_id, parent_branch_id, fork_message_id, name, created_at "
        "FROM branches WHERE conversation_id = ? ORDER BY created_at, id",
        (conversation_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_message(connection: sqlite3.Connection, message_id: str) -> dict[str, object] | None:
    row = connection.execute(
        "SELECT id, branch_id, seq, role, participant, content, model_ref, created_at "
        "FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def list_own_messages(
    connection: sqlite3.Connection, branch_id: str, upto_seq: int | None = None
) -> list[dict[str, object]]:
    if upto_seq is None:
        rows = connection.execute(
            "SELECT id, branch_id, seq, role, participant, content, model_ref, created_at "
            "FROM messages WHERE branch_id = ? ORDER BY seq",
            (branch_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT id, branch_id, seq, role, participant, content, model_ref, created_at "
            "FROM messages WHERE branch_id = ? AND seq <= ? ORDER BY seq",
            (branch_id, upto_seq),
        ).fetchall()
    return [dict(row) for row in rows]


def insert_message(
    connection: sqlite3.Connection,
    branch_id: str,
    role: str,
    participant: str,
    content: str,
    model_ref: str | None,
) -> dict[str, object]:
    message_id = new_id()
    created_at = utc_now()
    # A single INSERT...SELECT obtains the next sequence while holding SQLite's
    # writer lock, avoiding a read-then-write race between concurrent appends.
    connection.execute(
        "INSERT INTO messages(id, branch_id, seq, role, participant, content, model_ref, created_at) "
        "SELECT ?, ?, COALESCE(MAX(seq), 0) + 1, ?, ?, ?, ?, ? "
        "FROM messages WHERE branch_id = ?",
        (
            message_id,
            branch_id,
            role,
            participant,
            content,
            model_ref,
            created_at,
            branch_id,
        ),
    )
    return get_message(connection, message_id)
