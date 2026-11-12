"""Immutable one-per-run context snapshot persistence."""

from __future__ import annotations

import json
import sqlite3

from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now


def create_snapshot(
    connection: sqlite3.Connection,
    run_id: str,
    provider_label: str,
    packet: dict[str, object],
    token_estimate: int,
) -> dict[str, object]:
    snapshot_id = new_id()
    created_at = utc_now()
    packet_json = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
    connection.execute(
        "INSERT INTO context_snapshots "
        "(id, run_id, provider_label, packet_json, token_estimate, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (snapshot_id, run_id, provider_label, packet_json, token_estimate, created_at),
    )
    return {
        "id": snapshot_id,
        "run_id": run_id,
        "provider_label": provider_label,
        "packet": packet,
        "token_estimate": token_estimate,
        "created_at": created_at,
    }


def get_snapshot(connection: sqlite3.Connection, run_id: str) -> dict[str, object] | None:
    row = connection.execute(
        "SELECT id, run_id, provider_label, packet_json, token_estimate, created_at "
        "FROM context_snapshots WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": str(row["id"]),
        "run_id": str(row["run_id"]),
        "provider_label": str(row["provider_label"]),
        "packet": json.loads(str(row["packet_json"])),
        "token_estimate": int(row["token_estimate"]),
        "created_at": str(row["created_at"]),
    }
