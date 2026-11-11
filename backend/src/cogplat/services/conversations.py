"""Transactional project, conversation, branch, and history services."""

from __future__ import annotations

import sqlite3

from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now
from cogplat.repos import conversations as conversation_repo
from cogplat.repos import projects as project_repo


class ResourceNotFound(Exception):
    """A requested project, conversation, branch, or message does not exist."""


class InvalidFork(Exception):
    """A fork target is not visible in the selected parent branch."""


def create_project(
    connection: sqlite3.Connection, name: str, description: str | None = None
) -> dict[str, object]:
    with connection:
        return project_repo.create_project(connection, name, description)


def list_projects(connection: sqlite3.Connection) -> list[dict[str, object]]:
    return project_repo.list_projects(connection)


def create_conversation(
    connection: sqlite3.Connection, title: str, project_id: str | None = None
) -> dict[str, object]:
    if project_id is not None and project_repo.get_project(connection, project_id) is None:
        raise ResourceNotFound("Project not found.")

    conversation_id = new_id()
    root_branch_id = new_id()
    created_at = utc_now()
    with connection:
        connection.execute(
            "INSERT INTO conversations(id, project_id, title, root_branch_id, created_at) "
            "VALUES (?, ?, ?, NULL, ?)",
            (conversation_id, project_id, title, created_at),
        )
        connection.execute(
            "INSERT INTO branches(id, conversation_id, parent_branch_id, fork_message_id, name, created_at) "
            "VALUES (?, ?, NULL, NULL, 'Main', ?)",
            (root_branch_id, conversation_id, created_at),
        )
        connection.execute(
            "UPDATE conversations SET root_branch_id = ? WHERE id = ?",
            (root_branch_id, conversation_id),
        )
    return conversation_repo.get_conversation(connection, conversation_id)


def list_conversations(
    connection: sqlite3.Connection, project_id: str | None = None
) -> list[dict[str, object]]:
    return conversation_repo.list_conversations(connection, project_id)


def list_branches(
    connection: sqlite3.Connection, conversation_id: str
) -> list[dict[str, object]]:
    if conversation_repo.get_conversation(connection, conversation_id) is None:
        raise ResourceNotFound("Conversation not found.")
    return conversation_repo.list_branches(connection, conversation_id)


def append_message(
    connection: sqlite3.Connection,
    branch_id: str,
    role: str,
    participant: str,
    content: str,
    model_ref: str | None = None,
) -> dict[str, object]:
    if conversation_repo.get_branch(connection, branch_id) is None:
        raise ResourceNotFound("Branch not found.")
    with connection:
        return conversation_repo.insert_message(
            connection, branch_id, role, participant, content, model_ref
        )


def resolve_history(
    connection: sqlite3.Connection, branch_id: str
) -> list[dict[str, object]]:
    """Resolve own messages and the exact inherited ancestry cutoff.

    A fork may target any message visible in the parent branch, including a
    message inherited from an ancestor. Each ancestor contributes only the
    portion that was visible at the next branch's own fork point.
    """

    current = conversation_repo.get_branch(connection, branch_id)
    if current is None:
        raise ResourceNotFound("Branch not found.")

    segments: list[list[dict[str, object]]] = []
    cutoff_message_id: str | None = None

    while current is not None:
        if cutoff_message_id is None:
            segments.append(
                conversation_repo.list_own_messages(connection, str(current["id"]))
            )
        else:
            cutoff_message = conversation_repo.get_message(connection, cutoff_message_id)
            if cutoff_message is None:
                raise RuntimeError("Branch references a missing fork message.")
            if cutoff_message["branch_id"] == current["id"]:
                segments.append(
                    conversation_repo.list_own_messages(
                        connection, str(current["id"]), int(cutoff_message["seq"])
                    )
                )
                # Continue upward using this branch's own fork point. Stopping
                # here would lose the inherited history before this branch.
                cutoff_message_id = (
                    str(current["fork_message_id"])
                    if current["fork_message_id"] is not None
                    else None
                )
                parent_id = current["parent_branch_id"]
                if parent_id is None:
                    break
                current = conversation_repo.get_branch(connection, str(parent_id))
                continue
            segments.append([])

        parent_id = current["parent_branch_id"]
        if parent_id is None:
            break
        if cutoff_message_id is None:
            cutoff_message_id = str(current["fork_message_id"])
        current = conversation_repo.get_branch(connection, str(parent_id))

    resolved: list[dict[str, object]] = []
    for segment in reversed(segments):
        resolved.extend(segment)
    return resolved


def fork_branch(
    connection: sqlite3.Connection,
    parent_branch_id: str,
    fork_message_id: str,
    name: str,
) -> dict[str, object]:
    parent = conversation_repo.get_branch(connection, parent_branch_id)
    if parent is None:
        raise ResourceNotFound("Parent branch not found.")

    visible_ids = {message["id"] for message in resolve_history(connection, parent_branch_id)}
    if fork_message_id not in visible_ids:
        raise InvalidFork("Fork message must be visible in the selected parent branch.")

    branch_id = new_id()
    created_at = utc_now()
    with connection:
        connection.execute(
            "INSERT INTO branches(id, conversation_id, parent_branch_id, fork_message_id, name, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                branch_id,
                parent["conversation_id"],
                parent_branch_id,
                fork_message_id,
                name,
                created_at,
            ),
        )
    return conversation_repo.get_branch(connection, branch_id)
