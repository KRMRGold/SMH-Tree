"""Permission-filtered unified search across messages, memory, and claims."""
from __future__ import annotations

import re
import sqlite3

from cogplat.services import epistemic, memory, conversations
from cogplat.services.permissions import AccessContext


def _fts_query(query: str) -> str | None:
    terms = re.findall(r"[\w]+", query, flags=re.UNICODE)
    if not terms:
        return None
    return " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)


def search_records(connection: sqlite3.Connection, ctx: AccessContext, query: str,
                   *, memory_scope: str | None = None, limit: int = 50):
    """Return a stable, bounded union of records visible in the supplied context."""
    fts = _fts_query(query)
    if fts is None:
        return {"items": [], "message_search_scope": "branch" if ctx.branch_id else "unavailable"}

    items: list[dict[str, object]] = []
    claims = epistemic.list_claims(connection, ctx, query=query, limit=limit, offset=0)
    items.extend({"type": "claim", "record": item} for item in claims)

    memories = memory.list_memory(
        connection, ctx, query=query, scope=memory_scope, state="active",
        limit=limit, offset=0,
    )
    items.extend({"type": "memory", "record": item} for item in memories)

    if ctx.branch_id is not None:
        visible_ids = [
            str(item["id"])
            for item in conversations.resolve_history(connection, ctx.branch_id)
        ]
        if visible_ids:
            placeholders = ",".join("?" for _ in visible_ids)
            rows = connection.execute(
                "SELECT m.* FROM messages m JOIN messages_fts f ON f.rowid = m.rowid "
                f"WHERE messages_fts MATCH ? AND m.id IN ({placeholders}) "
                "ORDER BY m.created_at DESC, m.id LIMIT ?",
                [fts, *visible_ids, limit],
            ).fetchall()
            items.extend({"type": "message", "record": dict(row)} for row in rows)

    items.sort(
        key=lambda item: (
            str(item["record"].get("created_at", "")),
            str(item["record"].get("id", "")),
        ),
        reverse=True,
    )
    return {
        "items": items[:limit],
        "message_search_scope": "branch" if ctx.branch_id else "not_requested",
    }
