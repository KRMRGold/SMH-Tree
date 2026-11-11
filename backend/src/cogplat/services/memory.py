"""Memory CRUD, lifecycle, FTS search, and deterministic scope filtering."""
from __future__ import annotations
import re
import sqlite3
from collections.abc import Mapping
from cogplat.domain.memory import MemoryCreate, MemoryItem, MemoryLifecycleUpdate
from cogplat.repos import memory as memory_repo
from cogplat.services.permissions import AccessContext, remote_memory_sharing_enabled, visible_memory_scopes

class ResourceNotFound(Exception):
    """A memory item or referenced scope does not exist."""
class InvalidMemoryScope(Exception):
    """The requested memory scope is malformed or does not exist."""
class InvalidMemoryTransition(Exception):
    """A memory lifecycle transition is invalid."""

def _validate_scope_exists(connection: sqlite3.Connection, scope: str, scope_id: str | None) -> None:
    if scope in {"global", "user"}:
        if scope_id is not None:
            raise InvalidMemoryScope(f"{scope} memory must not have a scope_id.")
        return
    if not scope_id:
        raise InvalidMemoryScope(f"{scope} memory requires a scope_id.")
    table = {"project": "projects", "conversation": "conversations", "branch": "branches"}.get(scope)
    if table is not None and connection.execute(
        f"SELECT id FROM {table} WHERE id = ?", (scope_id,)
    ).fetchone() is None:
        raise ResourceNotFound(f"{scope.title()} scope not found.")

def create_memory(connection: sqlite3.Connection, payload: MemoryCreate) -> dict[str, object]:
    _validate_scope_exists(connection, payload.scope, payload.scope_id)
    if not payload.content.strip():
        raise InvalidMemoryScope("Memory content must contain non-whitespace text.")
    with connection:
        item = memory_repo.insert_memory_item(
            connection, scope=payload.scope, scope_id=payload.scope_id, kind=payload.kind,
            content=payload.content, importance=payload.importance,
            origin_kind=payload.origin_kind, origin_ref=payload.origin_ref,
        )
    return MemoryItem.model_validate(item).model_dump()

def _item_is_visible(connection: sqlite3.Connection, item: Mapping[str, object],
                      ctx: AccessContext) -> bool:
    scope, scope_id = str(item["scope"]), item["scope_id"]
    if scope in {"global", "user"}:
        return not (ctx.allow_remote and not remote_memory_sharing_enabled(connection, scope))
    if scope == "project":
        return ctx.project_id is not None and scope_id == ctx.project_id
    if scope == "conversation":
        return ctx.conversation_id is not None and scope_id == ctx.conversation_id
    if scope == "agent":
        return ctx.agent_id is not None and scope_id == ctx.agent_id
    if scope == "branch":
        cutoffs = dict(ctx.branch_scope_cutoffs)
        if not cutoffs and ctx.branch_id is not None:
            cutoffs[ctx.branch_id] = None
        if scope_id not in cutoffs:
            return False
        cutoff = cutoffs[str(scope_id)]
        return cutoff is None or str(item["created_at"]) <= cutoff
    return False

def get_memory(connection: sqlite3.Connection, memory_id: str,
               ctx: AccessContext) -> dict[str, object]:
    item = memory_repo.get_memory_item(connection, memory_id)
    if item is None or not _item_is_visible(connection, item, ctx):
        raise ResourceNotFound("Memory item not found.")
    return MemoryItem.model_validate(item).model_dump()

def list_memory(connection: sqlite3.Connection, ctx: AccessContext, *,
                query: str | None = None, scope: str | None = None,
                state: str = "active", limit: int = 50, offset: int = 0) -> list[dict[str, object]]:
    valid_scopes = {"global", "user", "project", "conversation", "branch", "agent"}
    valid_states = {"active", "outdated", "superseded", "archived", "all"}
    if scope is not None and scope not in valid_scopes:
        raise InvalidMemoryScope("Unknown memory scope.")
    if state not in valid_states:
        raise InvalidMemoryScope("Unknown memory state.")
    scopes = visible_memory_scopes(ctx)
    if scope is not None:
        scopes = [entry for entry in scopes if entry[0] == scope]
    clauses: list[str] = []
    params: list[object] = []
    cutoffs = dict(ctx.branch_scope_cutoffs)
    if not cutoffs and ctx.branch_id is not None:
        cutoffs[ctx.branch_id] = None
    for item_scope, scope_id in scopes:
        if ctx.allow_remote and item_scope in {"global", "user"}:
            if not remote_memory_sharing_enabled(connection, item_scope):
                continue
        if item_scope == "branch":
            cutoff = cutoffs.get(str(scope_id))
            if cutoff is None:
                clauses.append("(scope = ? AND scope_id = ?)")
                params.extend((item_scope, scope_id))
            else:
                clauses.append("(scope = ? AND scope_id = ? AND created_at <= ?)")
                params.extend((item_scope, scope_id, cutoff))
        elif scope_id is None:
            clauses.append("(scope = ? AND scope_id IS NULL)")
            params.append(item_scope)
        else:
            clauses.append("(scope = ? AND scope_id = ?)")
            params.extend((item_scope, scope_id))
    if not clauses:
        return []
    where = "(" + " OR ".join(clauses) + ")"
    if state != "all":
        where += " AND state = ?"
        params.append(state)
    fts_query = None
    if query is not None and query.strip():
        terms = re.findall(r"[\w]+", query, flags=re.UNICODE)
        if not terms:
            return []
        fts_query = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
    if fts_query is None:
        sql = (
            "SELECT id, scope, scope_id, kind, content, importance, state, superseded_by, "
            "origin_kind, origin_ref, created_at, updated_at FROM memory_items "
            f"WHERE {where} ORDER BY importance DESC, created_at DESC, id LIMIT ? OFFSET ?"
        )
    else:
        sql = (
            "SELECT mi.id, mi.scope, mi.scope_id, mi.kind, mi.content, mi.importance, "
            "mi.state, mi.superseded_by, mi.origin_kind, mi.origin_ref, mi.created_at, mi.updated_at "
            "FROM memory_items mi JOIN memory_fts ON memory_fts.rowid = mi.rowid "
            f"WHERE memory_fts MATCH ? AND {where} "
            "ORDER BY mi.importance DESC, mi.created_at DESC, mi.id LIMIT ? OFFSET ?"
        )
        params.insert(0, fts_query)
    params.extend((limit, offset))
    rows = connection.execute(sql, params).fetchall()
    return [MemoryItem.model_validate(dict(row)).model_dump() for row in rows]

def update_memory_lifecycle(connection: sqlite3.Connection, memory_id: str,
                             payload: MemoryLifecycleUpdate) -> dict[str, object]:
    current = memory_repo.get_memory_item(connection, memory_id)
    if current is None:
        raise ResourceNotFound("Memory item not found.")
    current_state = str(current["state"])
    if current_state in {"superseded", "archived"}:
        raise InvalidMemoryTransition("Superseded or archived memory cannot transition again.")
    if payload.state == "outdated" and current_state != "active":
        raise InvalidMemoryTransition("Only active memory can be marked outdated.")
    if payload.state == "superseded":
        target = memory_repo.get_memory_item(connection, str(payload.superseded_by))
        if target is None:
            raise ResourceNotFound("Replacement memory item not found.")
        if target["id"] == memory_id:
            raise InvalidMemoryTransition("A memory item cannot supersede itself.")
        if target["scope"] != current["scope"] or target["scope_id"] != current["scope_id"]:
            raise InvalidMemoryTransition("Replacement memory must have the same scope and scope_id.")
        if target["state"] != "active":
            raise InvalidMemoryTransition("Replacement memory must be active.")
    with connection:
        item = memory_repo.set_memory_state(connection, memory_id, payload.state, payload.superseded_by)
    return MemoryItem.model_validate(item).model_dump()
