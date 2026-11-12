"""Persistence operations for epistemic records."""
from __future__ import annotations

import re
import sqlite3

from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now


def _dict(row):
    return dict(row) if row is not None else None


def _fts_query(query: str | None) -> str | None:
    if not query or not query.strip():
        return None
    terms = re.findall(r"[\w]+", query, flags=re.UNICODE)
    if not terms:
        return None
    return " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)


def create_source(connection: sqlite3.Connection, *, project_id: str | None,
                  kind: str, title: str | None, uri: str | None,
                  content_hash: str | None, retrieved_at: str | None):
    source_id, now = new_id(), utc_now()
    connection.execute(
        "INSERT INTO sources(id, project_id, kind, title, uri, content_hash, retrieved_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (source_id, project_id, kind, title, uri, content_hash, retrieved_at, now),
    )
    return get_source(connection, source_id)


def get_source(connection: sqlite3.Connection, source_id: str):
    return _dict(connection.execute(
        "SELECT * FROM sources WHERE id = ?", (source_id,)
    ).fetchone())


def list_sources(connection: sqlite3.Connection, project_id: str | None, limit: int, offset: int):
    if project_id is None:
        rows = connection.execute(
            "SELECT * FROM sources WHERE project_id IS NULL ORDER BY created_at DESC, id LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM sources WHERE project_id IS NULL OR project_id = ? "
            "ORDER BY created_at DESC, id LIMIT ? OFFSET ?",
            (project_id, limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def create_claim(connection: sqlite3.Connection, *, project_id: str | None,
                 claim_type: str, text: str, subject: str | None,
                 predicate: str | None, object_value: str | None,
                 valid_from: str | None, valid_to: str | None,
                 origin_kind: str, origin_ref: str | None):
    claim_id, now = new_id(), utc_now()
    connection.execute(
        "INSERT INTO claims(id, project_id, claim_type, text, subject, predicate, object, "
        "valid_from, valid_to, origin_kind, origin_ref, observed_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (claim_id, project_id, claim_type, text, subject, predicate, object_value,
         valid_from, valid_to, origin_kind, origin_ref, now, now),
    )
    return claim_id


def append_status(connection: sqlite3.Connection, claim_id: str, *, status: str,
                  scope: str, policy: str | None, rationale: str | None,
                  actor_kind: str, actor_ref: str | None):
    event_id, now = new_id(), utc_now()
    connection.execute(
        "INSERT INTO claim_status_events(id, claim_id, status, scope, policy, rationale, "
        "actor_kind, actor_ref, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (event_id, claim_id, status, scope, policy, rationale, actor_kind, actor_ref, now),
    )
    return event_id


def append_assessment(connection: sqlite3.Connection, claim_id: str, *, dimension: str,
                      value_num: float | None, value_text: str | None,
                      rationale: str | None, actor_kind: str, actor_ref: str | None):
    assessment_id, now = new_id(), utc_now()
    connection.execute(
        "INSERT INTO claim_assessments(id, claim_id, dimension, value_num, value_text, "
        "rationale, actor_kind, actor_ref, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (assessment_id, claim_id, dimension, value_num, value_text, rationale,
         actor_kind, actor_ref, now),
    )
    return assessment_id


def append_evidence(connection: sqlite3.Connection, claim_id: str, *, source_id: str,
                    stance: str, excerpt: str | None, locator: str | None):
    evidence_id, now = new_id(), utc_now()
    connection.execute(
        "INSERT INTO evidence(id, claim_id, source_id, stance, excerpt, locator, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (evidence_id, claim_id, source_id, stance, excerpt, locator, now),
    )
    return evidence_id


def append_relation(connection: sqlite3.Connection, from_claim_id: str, to_claim_id: str,
                    *, rel: str, contradiction_basis: str | None, note: str | None):
    relation_id, now = new_id(), utc_now()
    connection.execute(
        "INSERT INTO claim_relations(id, from_claim_id, to_claim_id, rel, "
        "contradiction_basis, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (relation_id, from_claim_id, to_claim_id, rel, contradiction_basis, note, now),
    )
    return relation_id


def create_open_question(connection: sqlite3.Connection, *, project_id: str | None,
                         text: str, related_claim_id: str | None):
    question_id, now = new_id(), utc_now()
    connection.execute(
        "INSERT INTO open_questions(id, project_id, text, state, related_claim_id, created_at) "
        "VALUES (?, ?, ?, 'open', ?, ?)",
        (question_id, project_id, text, related_claim_id, now),
    )
    return question_id


def update_open_question(connection: sqlite3.Connection, question_id: str, state: str):
    connection.execute(
        "UPDATE open_questions SET state = ? WHERE id = ?", (state, question_id)
    )
    return _dict(connection.execute(
        "SELECT * FROM open_questions WHERE id = ?", (question_id,)
    ).fetchone())


def get_open_question(connection: sqlite3.Connection, question_id: str):
    return _dict(connection.execute(
        "SELECT * FROM open_questions WHERE id = ?", (question_id,)
    ).fetchone())


def list_open_questions(connection: sqlite3.Connection, project_id: str | None,
                        state: str | None, limit: int, offset: int):
    clauses = ["(project_id IS NULL OR project_id = ?)"] if project_id is not None else ["project_id IS NULL"]
    params: list[object] = [project_id] if project_id is not None else []
    if state is not None:
        clauses.append("state = ?")
        params.append(state)
    params.extend((limit, offset))
    rows = connection.execute(
        "SELECT * FROM open_questions WHERE " + " AND ".join(clauses) +
        " ORDER BY created_at DESC, id LIMIT ? OFFSET ?", params
    ).fetchall()
    return [dict(row) for row in rows]


def get_claim(connection: sqlite3.Connection, claim_id: str):
    claim = _dict(connection.execute(
        "SELECT * FROM claims WHERE id = ?", (claim_id,)
    ).fetchone())
    if claim is None:
        return None

    statuses = connection.execute(
        "SELECT * FROM claim_status_events WHERE claim_id = ? "
        "ORDER BY created_at DESC, id DESC", (claim_id,)
    ).fetchall()
    latest_status: dict[str, dict[str, object]] = {}
    for row in statuses:
        item = dict(row)
        latest_status.setdefault(str(item["scope"]), item)

    assessments = connection.execute(
        "SELECT * FROM claim_assessments WHERE claim_id = ? "
        "ORDER BY created_at DESC, id DESC", (claim_id,)
    ).fetchall()
    latest_assessment: dict[str, dict[str, object]] = {}
    for row in assessments:
        item = dict(row)
        latest_assessment.setdefault(str(item["dimension"]), item)

    evidence_rows = connection.execute(
        "SELECT e.*, s.kind AS source_kind, s.title AS source_title, "
        "s.uri AS source_uri, s.project_id AS source_project_id "
        "FROM evidence e JOIN sources s ON s.id = e.source_id "
        "WHERE e.claim_id = ? ORDER BY e.created_at, e.id", (claim_id,)
    ).fetchall()

    relation_rows = connection.execute(
        "SELECT r.*, c.text AS related_claim_text, c.project_id AS related_project_id "
        "FROM claim_relations r JOIN claims c ON c.id = "
        "CASE WHEN r.from_claim_id = ? THEN r.to_claim_id ELSE r.from_claim_id END "
        "WHERE r.from_claim_id = ? OR r.to_claim_id = ? "
        "ORDER BY r.created_at, r.id", (claim_id, claim_id, claim_id)
    ).fetchall()

    claim["current_status"] = list(latest_status.values())
    claim["assessments"] = list(latest_assessment.values())
    claim["evidence"] = [dict(row) for row in evidence_rows]
    claim["relations"] = [dict(row) for row in relation_rows]
    return claim


def list_claims(connection: sqlite3.Connection, project_id: str | None,
                query: str | None, limit: int, offset: int):
    fts = _fts_query(query)
    if query is not None and query.strip() and fts is None:
        return []
    params: list[object] = []
    visibility = "c.project_id IS NULL" if project_id is None else "(c.project_id IS NULL OR c.project_id = ?)"
    if project_id is not None:
        params.append(project_id)
    if fts is None:
        sql = f"SELECT c.id FROM claims c WHERE {visibility} ORDER BY c.created_at DESC, c.id LIMIT ? OFFSET ?"
    else:
        sql = (
            "SELECT c.id FROM claims c JOIN claims_fts ON claims_fts.rowid = c.rowid "
            f"WHERE claims_fts MATCH ? AND {visibility} "
            "ORDER BY bm25(claims_fts), c.created_at DESC, c.id LIMIT ? OFFSET ?"
        )
        params.insert(0, fts)
    params.extend((limit, offset))
    ids = [str(row["id"]) for row in connection.execute(sql, params).fetchall()]
    return [get_claim(connection, claim_id) for claim_id in ids]
