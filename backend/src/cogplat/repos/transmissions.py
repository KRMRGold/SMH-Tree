"""Append-only persistence for outbound remote transmissions."""
from __future__ import annotations
import json
import sqlite3
from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now

def record_transmission(connection: sqlite3.Connection, run_id: str, provider_label: str, item_refs: list[str], byte_count: int) -> dict[str, object]:
    transmission_id = new_id()
    created_at = utc_now()
    with connection:
        connection.execute(
            "INSERT INTO remote_transmissions (id, run_id, provider_label, item_refs_json, byte_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (transmission_id, run_id, provider_label, json.dumps(item_refs, separators=(",", ":")), byte_count, created_at),
        )
    return {"id": transmission_id, "run_id": run_id, "provider_label": provider_label, "item_refs": item_refs, "byte_count": byte_count, "created_at": created_at}

def list_transmissions(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute("SELECT id, run_id, provider_label, item_refs_json, byte_count, created_at FROM remote_transmissions ORDER BY created_at DESC, id DESC").fetchall()
    return [
        {"id": str(row["id"]), "run_id": str(row["run_id"]), "provider_label": str(row["provider_label"]), "item_refs": json.loads(str(row["item_refs_json"])), "byte_count": int(row["byte_count"]), "created_at": str(row["created_at"])}
        for row in rows
    ]
