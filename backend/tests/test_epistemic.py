"""M6 epistemic records, scope, provenance, and compiler tests."""
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from cogplat.config import Settings
from cogplat.db.connection import apply_migrations, connect_db
from cogplat.domain.context import CompileRequest
from cogplat.domain.epistemic import (
    ClaimAssessmentCreate, ClaimCreate, ClaimRelationCreate, ClaimStatusCreate,
    EvidenceCreate, OpenQuestionCreate, OpenQuestionUpdate, SourceCreate,
)
from cogplat.main import create_app
from cogplat.services import conversations, context_compiler, epistemic
from cogplat.services.permissions import build_access_context


def make_db(path):
    connection = connect_db(path)
    assert apply_migrations(connection) == 5
    return connection


def make_project(connection, project_id="p1"):
    connection.execute(
        "INSERT INTO projects(id, name, description, created_at) "
        "VALUES (?, 'Project', 'Project context', '2026-01-01T00:00:00Z')",
        (project_id,),
    )


def claim_payload(text, project_id="p1", origin_kind="user"):
    return ClaimCreate(
        project_id=project_id, claim_type="factual", text=text,
        origin_kind=origin_kind,
    )


def test_claim_creation_records_origin_derived_initial_status(tmp_path):
    connection = make_db(tmp_path / "claim.db")
    try:
        make_project(connection)
        with connection:
            reported = epistemic.create_claim(connection, claim_payload("A user statement"))
            proposed = epistemic.create_claim(
                connection, claim_payload("A model extraction", origin_kind="extraction")
            )
            imported = epistemic.create_claim(
                connection, claim_payload("An imported claim", origin_kind="import")
            )
        assert reported["current_status"][0]["status"] == "reported"
        assert proposed["current_status"][0]["status"] == "proposed"
        assert imported["current_status"][0]["status"] == "unknown"
        assert reported["origin_kind"] == "user"
    finally:
        connection.close()


def test_status_is_latest_per_scope_and_accepted_requires_policy(tmp_path):
    connection = make_db(tmp_path / "status.db")
    try:
        make_project(connection)
        claim = epistemic.create_claim(connection, claim_payload("A scoped claim"))
        ctx = build_access_context(connection, project_id="p1")
        with pytest.raises(ValidationError):
            ClaimStatusCreate(status="accepted")
        epistemic.append_claim_status(
            connection, claim["id"],
            ClaimStatusCreate(status="contested", scope="default", rationale="Conflicting evidence"),
            ctx,
        )
        epistemic.append_claim_status(
            connection, claim["id"],
            ClaimStatusCreate(status="accepted", scope="project:p1", policy="manual-review"),
            ctx,
        )
        result = epistemic.get_claim(connection, claim["id"], ctx)
        statuses = {item["scope"]: item["status"] for item in result["current_status"]}
        assert statuses == {"default": "contested", "project:p1": "accepted"}
    finally:
        connection.close()


def test_assessments_keep_dimensions_separate_and_project_latest_per_dimension(tmp_path):
    connection = make_db(tmp_path / "assessment.db")
    try:
        make_project(connection)
        claim = epistemic.create_claim(connection, claim_payload("Assessment target"))
        ctx = build_access_context(connection, project_id="p1")
        epistemic.append_claim_assessment(
            connection, claim["id"],
            ClaimAssessmentCreate(dimension="source_reliability", value_num=0.8), ctx,
        )
        epistemic.append_claim_assessment(
            connection, claim["id"],
            ClaimAssessmentCreate(dimension="evidence_strength", value_num=0.4), ctx,
        )
        epistemic.append_claim_assessment(
            connection, claim["id"],
            ClaimAssessmentCreate(dimension="source_reliability", value_num=0.9), ctx,
        )
        result = epistemic.get_claim(connection, claim["id"], ctx)
        assessments = {item["dimension"]: item["value_num"] for item in result["assessments"]}
        assert assessments == {"source_reliability": 0.9, "evidence_strength": 0.4}
        assert len(connection.execute(
            "SELECT id FROM claim_assessments WHERE claim_id = ?", (claim["id"],)
        ).fetchall()) == 3
    finally:
        connection.close()


def test_evidence_requires_visible_source_and_returns_locator(tmp_path):
    connection = make_db(tmp_path / "evidence.db")
    try:
        make_project(connection)
        claim = epistemic.create_claim(connection, claim_payload("Evidence-backed claim"))
        source = epistemic.create_source(
            connection, SourceCreate(project_id="p1", kind="document", title="Report", uri="file:report.pdf")
        )
        ctx = build_access_context(connection, project_id="p1")
        result = epistemic.add_evidence(
            connection, claim["id"],
            EvidenceCreate(source_id=source["id"], stance="supports",
                           excerpt="Relevant passage", locator="page 4, lines 2-5"),
            ctx,
        )
        assert result["evidence"][0]["source_id"] == source["id"]
        assert result["evidence"][0]["locator"] == "page 4, lines 2-5"
        other_ctx = build_access_context(connection)
        with pytest.raises(epistemic.ResourceNotFound):
            epistemic.add_evidence(
                connection, claim["id"],
                EvidenceCreate(source_id=source["id"], stance="supports"), other_ctx,
            )
    finally:
        connection.close()


def test_contradiction_is_a_separate_relation_and_does_not_mutate_partner(tmp_path):
    connection = make_db(tmp_path / "relations.db")
    try:
        make_project(connection)
        first = epistemic.create_claim(connection, claim_payload("The result is positive"))
        second = epistemic.create_claim(connection, claim_payload("The result is negative"))
        ctx = build_access_context(connection, project_id="p1")
        epistemic.append_claim_status(
            connection, first["id"],
            ClaimStatusCreate(status="contested", rationale="Conflicting reports"), ctx,
        )
        result = epistemic.add_relation(
            connection, first["id"],
            ClaimRelationCreate(
                to_claim_id=second["id"], rel="contradicts",
                contradiction_basis="direct", note="Opposing result",
            ),
            ctx,
        )
        partner = epistemic.get_claim(connection, second["id"], ctx)
        assert result["relations"][0]["contradiction_basis"] == "direct"
        assert partner["current_status"][0]["status"] == "reported"
        assert partner["relations"][0]["from_claim_id"] == first["id"]
    finally:
        connection.close()


def test_epistemic_history_tables_are_append_only(tmp_path):
    connection = make_db(tmp_path / "append-only.db")
    try:
        make_project(connection)
        claim = epistemic.create_claim(connection, claim_payload("Immutable claim"))
        source = epistemic.create_source(
            connection, SourceCreate(project_id="p1", kind="document", title="Source")
        )
        ctx = build_access_context(connection, project_id="p1")
        epistemic.append_claim_assessment(
            connection, claim["id"],
            ClaimAssessmentCreate(dimension="evidence_strength", value_num=0.7), ctx,
        )
        epistemic.add_evidence(
            connection, claim["id"], EvidenceCreate(source_id=source["id"], stance="context"), ctx
        )
        partner = epistemic.create_claim(connection, claim_payload("Partner claim"))
        epistemic.add_relation(
            connection, claim["id"],
            ClaimRelationCreate(to_claim_id=partner["id"], rel="supports"), ctx
        )
        ids = {
            "claims": ("claims", claim["id"]),
            "sources": ("sources", source["id"]),
            "claim_status_events": (
                "claim_status_events",
                connection.execute(
                    "SELECT id FROM claim_status_events WHERE claim_id = ?", (claim["id"],)
                ).fetchone()["id"],
            ),
            "claim_assessments": (
                "claim_assessments",
                connection.execute(
                    "SELECT id FROM claim_assessments WHERE claim_id = ?", (claim["id"],)
                ).fetchone()["id"],
            ),
            "evidence": (
                "evidence",
                connection.execute(
                    "SELECT id FROM evidence WHERE claim_id = ?", (claim["id"],)
                ).fetchone()["id"],
            ),
            "claim_relations": (
                "claim_relations",
                connection.execute(
                    "SELECT id FROM claim_relations WHERE from_claim_id = ?", (claim["id"],)
                ).fetchone()["id"],
            ),
        }
        for table, record_id in ids.values():
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(f"UPDATE {table} SET id = id WHERE id = ?", (record_id,))
            connection.rollback()
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
            connection.rollback()
    finally:
        connection.close()


def test_project_visibility_and_open_question_transitions(tmp_path):
    connection = make_db(tmp_path / "questions.db")
    try:
        make_project(connection, "p1")
        make_project(connection, "p2")
        claim = epistemic.create_claim(connection, claim_payload("Private to project one", "p1"))
        with pytest.raises(epistemic.ResourceNotFound):
            epistemic.get_claim(connection, claim["id"], build_access_context(connection, project_id="p2"))
        question = epistemic.create_open_question(
            connection, OpenQuestionCreate(project_id="p1", text="What remains unknown?", related_claim_id=claim["id"])
        )
        ctx = build_access_context(connection, project_id="p1")
        investigating = epistemic.update_open_question(
            connection, question["id"], OpenQuestionUpdate(state="investigating"), ctx
        )
        assert investigating["state"] == "investigating"
        answered = epistemic.update_open_question(
            connection, question["id"], OpenQuestionUpdate(state="answered"), ctx
        )
        assert answered["state"] == "answered"
        with pytest.raises(epistemic.InvalidEpistemicRecord):
            epistemic.update_open_question(
                connection, question["id"], OpenQuestionUpdate(state="open"), ctx
            )
    finally:
        connection.close()


def test_claim_fts_search_returns_only_matching_visible_claims(tmp_path):
    connection = make_db(tmp_path / "fts.db")
    try:
        make_project(connection, "p1")
        make_project(connection, "p2")
        one = epistemic.create_claim(connection, claim_payload("Orchid flowers need bright light", "p1"))
        epistemic.create_claim(connection, claim_payload("Ocean tides follow lunar cycles", "p1"))
        epistemic.create_claim(connection, claim_payload("Orchid varieties grow in shade", "p2"))
        ctx = build_access_context(connection, project_id="p1")
        results = epistemic.list_claims(connection, ctx, query="orchid", limit=20, offset=0)
        assert [item["id"] for item in results] == [one["id"]]
        assert epistemic.list_claims(connection, ctx, query="???", limit=20, offset=0) == []
    finally:
        connection.close()


def test_compiler_includes_contested_claim_and_contradicting_partner(tmp_path):
    connection = make_db(tmp_path / "compiler-claims.db")
    try:
        make_project(connection)
        conversation = conversations.create_conversation(connection, "Epistemic context", "p1")
        branch_id = str(conversation["root_branch_id"])
        claim = epistemic.create_claim(
            connection, claim_payload("Orchid species require bright indirect light")
        )
        partner = epistemic.create_claim(
            connection, claim_payload("Orchid species require full direct sun")
        )
        ctx = build_access_context(connection, branch_id=branch_id)
        epistemic.append_claim_status(
            connection, claim["id"],
            ClaimStatusCreate(status="contested", rationale="Sources disagree"), ctx,
        )
        epistemic.add_relation(
            connection, claim["id"],
            ClaimRelationCreate(
                to_claim_id=partner["id"], rel="contradicts",
                contradiction_basis="different_context",
            ),
            ctx,
        )
        request = CompileRequest(
            access_context=ctx,
            current_user_message="What light do orchid species require?",
            current_user_message_id="current",
            history=[],
            provider_id="local",
            provider_label="Local",
            provider_is_remote=False,
            model="test-model",
            max_input_tokens=4096,
            reserve_output_tokens=256,
        )
        packet = context_compiler.compile_context(connection, request)
        claim_refs = {
            item["ref"] for item in packet.included_sources if item["type"] == "claim"
        }
        assert claim_refs == {claim["id"], partner["id"]}
        claim_messages = [
            message.content for message in packet.messages
            if message.content.startswith("Epistemic claim")
        ]
        assert any("default=contested" in text for text in claim_messages)
        assert any("full direct sun" in text for text in claim_messages)
    finally:
        connection.close()


def test_epistemic_api_requires_auth_and_exposes_claim_workflow(tmp_path):
    app = create_app(Settings(api_token="test-token", data_dir=tmp_path), providers={})
    client = TestClient(app)
    assert client.get("/v1/claims").status_code == 401
    auth = {"Authorization": "Bearer test-token"}
    project = client.post("/v1/projects", json={"name": "Research"}, headers=auth).json()
    claim = client.post(
        "/v1/claims",
        json={"project_id": project["id"], "claim_type": "factual", "text": "A testable statement"},
        headers=auth,
    )
    assert claim.status_code == 201
    assert claim.json()["current_status"][0]["status"] == "reported"
    status = client.post(
        f"/v1/claims/{claim.json()['id']}/status?project_id={project['id']}",
        json={"status": "accepted"},
        headers=auth,
    )
    assert status.status_code == 422
    accepted = client.post(
        f"/v1/claims/{claim.json()['id']}/status?project_id={project['id']}",
        json={"status": "accepted", "policy": "manual-review", "scope": f"project:{project['id']}"},
        headers=auth,
    )
    assert accepted.status_code == 201
    assert client.get(f"/v1/claims?project_id={project['id']}", headers=auth).json()["items"]
