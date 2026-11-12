"""Deterministic memory visibility and remote-sharing permissions."""
from __future__ import annotations
import json
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

@dataclass(frozen=True)
class AccessContext:
    user_id: str
    project_id: str | None
    conversation_id: str | None
    branch_id: str | None
    agent_id: str | None
    allow_remote: bool = False
    branch_scope_cutoffs: tuple[tuple[str, str | None], ...] = ()

class InvalidAccessContext(Exception):
    """The supplied project/conversation/branch context is inconsistent."""

def build_access_context(connection: sqlite3.Connection, *, project_id: str | None = None,
                         conversation_id: str | None = None, branch_id: str | None = None,
                         agent_id: str | None = None, allow_remote: bool = False) -> AccessContext:
    """Resolve and validate the context hierarchy, including branch fork cutoffs."""
    current = None
    if branch_id is not None:
        current = connection.execute(
            "SELECT id, conversation_id, parent_branch_id, fork_message_id FROM branches WHERE id = ?",
            (branch_id,),
        ).fetchone()
        if current is None:
            raise InvalidAccessContext("Branch not found.")
        actual_conversation_id = str(current["conversation_id"])
        if conversation_id is not None and conversation_id != actual_conversation_id:
            raise InvalidAccessContext("Branch does not belong to the supplied conversation.")
        conversation_id = actual_conversation_id

    if conversation_id is not None:
        conversation = connection.execute(
            "SELECT id, project_id FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if conversation is None:
            raise InvalidAccessContext("Conversation not found.")
        actual_project_id = conversation["project_id"]
        if project_id is not None and project_id != actual_project_id:
            raise InvalidAccessContext("Conversation does not belong to the supplied project.")
        project_id = str(actual_project_id) if actual_project_id is not None else None
    elif project_id is not None:
        if connection.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone() is None:
            raise InvalidAccessContext("Project not found.")

    cutoffs: list[tuple[str, str | None]] = []
    if branch_id is not None:
        seen: set[str] = set()
        inherited_cutoff: str | None = None
        first = True
        while current is not None:
            current_id = str(current["id"])
            if current_id in seen:
                raise InvalidAccessContext("Branch ancestry contains a cycle.")
            seen.add(current_id)
            cutoffs.append((current_id, None if first else inherited_cutoff))
            parent_id = current["parent_branch_id"]
            if parent_id is None:
                break
            fork = connection.execute(
                "SELECT created_at FROM messages WHERE id = ?", (current["fork_message_id"],)
            ).fetchone()
            if fork is None:
                raise InvalidAccessContext("Branch references a missing fork message.")
            inherited_cutoff = str(fork["created_at"])
            current = connection.execute(
                "SELECT id, conversation_id, parent_branch_id, fork_message_id FROM branches WHERE id = ?",
                (parent_id,),
            ).fetchone()
            if current is None:
                raise InvalidAccessContext("Branch references a missing parent.")
            first = False

    return AccessContext(
        user_id="local", project_id=project_id, conversation_id=conversation_id,
        branch_id=branch_id, agent_id=agent_id, allow_remote=allow_remote,
        branch_scope_cutoffs=tuple(cutoffs),
    )

def visible_memory_scopes(ctx: AccessContext) -> list[tuple[str, str | None]]:
    """Return eligible scope identifiers; branch cutoffs are carried separately."""
    scopes: list[tuple[str, str | None]] = [("global", None), ("user", None)]
    if ctx.project_id is not None:
        scopes.append(("project", ctx.project_id))
    if ctx.conversation_id is not None:
        scopes.append(("conversation", ctx.conversation_id))
    branch_ids = [branch_id for branch_id, _ in ctx.branch_scope_cutoffs]
    if not branch_ids and ctx.branch_id is not None:
        branch_ids = [ctx.branch_id]
    scopes.extend(("branch", branch_id) for branch_id in branch_ids)
    if ctx.agent_id is not None:
        scopes.append(("agent", ctx.agent_id))
    return scopes

def remote_memory_sharing_enabled(connection: sqlite3.Connection, scope: str) -> bool:
    if scope not in {"global", "user"}:
        raise ValueError("Only global and user memory have remote-sharing settings.")
    row = connection.execute(
        "SELECT value_json FROM settings WHERE key = ?", (f"share_{scope}_memory_remote",)
    ).fetchone()
    if row is None:
        return False
    try:
        return json.loads(str(row["value_json"])) is True
    except (TypeError, ValueError):
        return False

def filter_remote_memory_items(connection: sqlite3.Connection,
                               items: Iterable[Mapping[str, object]]) -> tuple[list[Mapping[str, object]], list[str]]:
    retained: list[Mapping[str, object]] = []
    dropped: list[str] = []
    for item in items:
        scope = str(item.get("scope", ""))
        if scope in {"global", "user"} and not remote_memory_sharing_enabled(connection, scope):
            dropped.append(str(item.get("id", item.get("ref", "unknown"))))
        else:
            retained.append(item)
    return retained, dropped

def can_read(connection: sqlite3.Connection, ctx: AccessContext,
             obj_type: str, obj_id: str) -> bool:
    """Check deterministic visibility for canonical records used by context sources."""
    if obj_type in {"claim", "source", "open_question"}:
        table = {
            "claim": "claims",
            "source": "sources",
            "open_question": "open_questions",
        }[obj_type]
        row = connection.execute(
            f"SELECT project_id FROM {table} WHERE id = ?", (obj_id,)
        ).fetchone()
        if row is None:
            return False
        project_id = row["project_id"]
        return project_id is None or (
            ctx.project_id is not None and str(project_id) == ctx.project_id
        )

    if obj_type == "message":
        if ctx.branch_id is None:
            return False
        from cogplat.services import conversations
        return any(
            str(message["id"]) == obj_id
            for message in conversations.resolve_history(connection, ctx.branch_id)
        )

    if obj_type == "memory_item":
        from cogplat.services import memory
        item = memory_repo_item(connection, obj_id)
        return item is not None and memory._item_is_visible(connection, item, ctx)

    raise ValueError(f"Unsupported object type for access check: {obj_type}")


def memory_repo_item(connection: sqlite3.Connection, memory_id: str):
    from cogplat.repos import memory as memory_repo
    return memory_repo.get_memory_item(connection, memory_id)

