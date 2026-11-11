"""Persistence for model runs and their ordered steps."""

from __future__ import annotations

import json
import sqlite3

from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now


def create_run(
    connection: sqlite3.Connection,
    kind: str,
    conversation_id: str,
    branch_id: str,
    allow_remote: bool,
    input_data: dict[str, object],
) -> dict[str, object]:
    run_id = new_id()
    created_at = utc_now()
    connection.execute(
        "INSERT INTO runs(id, kind, conversation_id, branch_id, status, allow_remote, "
        "input_json, created_at, started_at) VALUES (?, ?, ?, ?, 'running', ?, ?, ?, ?)",
        (run_id, kind, conversation_id, branch_id, int(allow_remote),
         json.dumps(input_data, separators=(",", ":")), created_at, created_at),
    )
    return get_run(connection, run_id)


def create_step(
    connection: sqlite3.Connection, run_id: str, name: str, status: str = "running"
) -> dict[str, object]:
    row = connection.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 FROM run_steps WHERE run_id = ?", (run_id,)
    ).fetchone()
    step_id = new_id()
    created_at = utc_now()
    seq = int(row[0])
    connection.execute(
        "INSERT INTO run_steps(id, run_id, seq, name, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (step_id, run_id, seq, name, status, created_at),
    )
    return {"id": step_id, "run_id": run_id, "seq": seq, "name": name, "status": status}


def finish_step(connection: sqlite3.Connection, step_id: str, status: str, detail: str | None = None):
    connection.execute(
        "UPDATE run_steps SET status = ?, detail_json = ? WHERE id = ?",
        (status, json.dumps({"message": detail}) if detail else None, step_id),
    )


def finish_run(
    connection: sqlite3.Connection,
    run_id: str,
    status: str,
    output_data: dict[str, object] | None = None,
    error: str | None = None,
):
    connection.execute(
        "UPDATE runs SET status = ?, output_json = ?, error = ?, finished_at = ? WHERE id = ?",
        (
            status,
            json.dumps(output_data, separators=(",", ":")) if output_data is not None else None,
            error,
            utc_now(),
            run_id,
        ),
    )


def get_run(connection: sqlite3.Connection, run_id: str) -> dict[str, object] | None:
    row = connection.execute(
        "SELECT id, kind, conversation_id, branch_id, status, allow_remote, input_json, "
        "output_json, error, started_at, finished_at, created_at FROM runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    for key in ("input_json", "output_json"):
        if result[key] is not None:
            result[key] = json.loads(result[key])
    result["steps"] = [
        dict(step) for step in connection.execute(
            "SELECT id, seq, name, status, detail_json, created_at FROM run_steps "
            "WHERE run_id = ? ORDER BY seq", (run_id,)
        ).fetchall()
    ]
    return result
