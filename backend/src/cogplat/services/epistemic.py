"""Validated service operations for the M6 epistemic layer."""
from __future__ import annotations

import sqlite3

from cogplat.domain.epistemic import (
    ClaimAssessmentCreate,
    ClaimCreate,
    ClaimRelationCreate,
    ClaimStatusCreate,
    EvidenceCreate,
    OpenQuestionCreate,
    OpenQuestionUpdate,
    SourceCreate,
)
from cogplat.repos import epistemic as epistemic_repo
from cogplat.services.permissions import AccessContext, can_read


class ResourceNotFound(Exception):
    """A requested epistemic record does not exist or is not visible."""


class InvalidEpistemicRecord(Exception):
    """An epistemic record violates a domain or scope rule."""


def _require_project(connection: sqlite3.Connection, project_id: str | None) -> None:
    if project_id is not None and connection.execute(
        "SELECT id FROM projects WHERE id = ?", (project_id,)
    ).fetchone() is None:
        raise ResourceNotFound("Project not found.")


def _require_visible(connection: sqlite3.Connection, ctx: AccessContext,
                     obj_type: str, obj_id: str) -> None:
    if not can_read(connection, ctx, obj_type, obj_id):
        raise ResourceNotFound(f"{obj_type.replace('_', ' ').title()} not found.")


def create_source(connection: sqlite3.Connection, payload: SourceCreate):
    _require_project(connection, payload.project_id)
    if payload.content_hash is not None:
        if any(ch not in "0123456789abcdefABCDEF" for ch in payload.content_hash):
            raise InvalidEpistemicRecord("content_hash must be a 64-character SHA-256 hex digest.")
    with connection:
        return epistemic_repo.create_source(
            connection, project_id=payload.project_id, kind=payload.kind,
            title=payload.title, uri=payload.uri, content_hash=payload.content_hash,
            retrieved_at=payload.retrieved_at,
        )


def list_sources(connection: sqlite3.Connection, ctx: AccessContext,
                 limit: int = 50, offset: int = 0):
    return epistemic_repo.list_sources(connection, ctx.project_id, limit, offset)


def get_source(connection: sqlite3.Connection, source_id: str, ctx: AccessContext):
    _require_visible(connection, ctx, "source", source_id)
    return epistemic_repo.get_source(connection, source_id)


def create_claim(connection: sqlite3.Connection, payload: ClaimCreate):
    _require_project(connection, payload.project_id)
    initial_status = {
        "user": "reported",
        "agent": "proposed",
        "extraction": "proposed",
        "import": "unknown",
    }[payload.origin_kind]
    actor_kind = "user" if payload.origin_kind == "user" else (
        "agent" if payload.origin_kind in {"agent", "extraction"} else "system"
    )
    origin_target = {
        "user": "message",
        "agent": "run",
        "extraction": "message",
        "import": "source",
    }[payload.origin_kind]
    if payload.origin_ref is not None:
        table = {"message": "messages", "run": "runs", "source": "sources"}[origin_target]
        if connection.execute(
            f"SELECT id FROM {table} WHERE id = ?", (payload.origin_ref,)
        ).fetchone() is None:
            raise ResourceNotFound(f"Origin {origin_target} not found.")

    with connection:
        claim_id = epistemic_repo.create_claim(
            connection, project_id=payload.project_id, claim_type=payload.claim_type,
            text=payload.text, subject=payload.subject, predicate=payload.predicate,
            object_value=payload.object, valid_from=payload.valid_from,
            valid_to=payload.valid_to.isoformat() if payload.valid_to else None,
            origin_kind=payload.origin_kind,
            origin_ref=payload.origin_ref,
        )
        if payload.origin_ref is not None:
            epistemic_repo.create_origin_link(
                connection, claim_id, target_type=origin_target,
                target_id=payload.origin_ref, actor_kind=actor_kind,
                actor_ref=payload.origin_ref,
            )
        epistemic_repo.append_status(
            connection, claim_id, status=initial_status, scope="default",
            policy=None, rationale="Initial status assigned from claim origin.",
            actor_kind=actor_kind, actor_ref=payload.origin_ref,
        )
    return epistemic_repo.get_claim(connection, claim_id)


def list_claims(connection: sqlite3.Connection, ctx: AccessContext, *,
                query: str | None = None, limit: int = 50, offset: int = 0):
    return epistemic_repo.list_claims(connection, ctx.project_id, query, limit, offset)


def get_claim(connection: sqlite3.Connection, claim_id: str, ctx: AccessContext):
    _require_visible(connection, ctx, "claim", claim_id)
    claim = epistemic_repo.get_claim(connection, claim_id)
    if claim is None:
        raise ResourceNotFound("Claim not found.")
    return claim


def append_claim_status(connection: sqlite3.Connection, claim_id: str,
                        payload: ClaimStatusCreate, ctx: AccessContext):
    claim = get_claim(connection, claim_id, ctx)
    scope = payload.scope
    if scope != "default":
        if not scope.startswith("project:"):
            raise InvalidEpistemicRecord("Status scope must be 'default' or 'project:<id>'.")
        scope_project_id = scope.removeprefix("project:")
        _require_project(connection, scope_project_id)
        if claim["project_id"] is not None and scope_project_id != claim["project_id"]:
            raise InvalidEpistemicRecord("Status scope must match the claim's project.")
        if ctx.project_id is not None and scope_project_id != ctx.project_id:
            raise ResourceNotFound("Claim not found.")
    with connection:
        epistemic_repo.append_status(
            connection, claim_id, status=payload.status, scope=scope,
            policy=payload.policy, rationale=payload.rationale,
            actor_kind=payload.actor_kind, actor_ref=payload.actor_ref,
        )
    return get_claim(connection, claim_id, ctx)


def append_claim_assessment(connection: sqlite3.Connection, claim_id: str,
                             payload: ClaimAssessmentCreate, ctx: AccessContext):
    get_claim(connection, claim_id, ctx)
    with connection:
        epistemic_repo.append_assessment(
            connection, claim_id, dimension=payload.dimension,
            value_num=payload.value_num, value_text=payload.value_text,
            rationale=payload.rationale, actor_kind=payload.actor_kind,
            actor_ref=payload.actor_ref,
        )
    return get_claim(connection, claim_id, ctx)


def add_evidence(connection: sqlite3.Connection, claim_id: str,
                 payload: EvidenceCreate, ctx: AccessContext):
    get_claim(connection, claim_id, ctx)
    _require_visible(connection, ctx, "source", payload.source_id)
    with connection:
        epistemic_repo.append_evidence(
            connection, claim_id, source_id=payload.source_id,
            stance=payload.stance, excerpt=payload.excerpt, locator=payload.locator,
        )
    return get_claim(connection, claim_id, ctx)


def add_relation(connection: sqlite3.Connection, claim_id: str,
                 payload: ClaimRelationCreate, ctx: AccessContext):
    get_claim(connection, claim_id, ctx)
    if claim_id == payload.to_claim_id:
        raise InvalidEpistemicRecord("A claim cannot be related to itself.")
    get_claim(connection, payload.to_claim_id, ctx)
    with connection:
        epistemic_repo.append_relation(
            connection, claim_id, payload.to_claim_id, rel=payload.rel,
            contradiction_basis=payload.contradiction_basis, note=payload.note,
        )
    return get_claim(connection, claim_id, ctx)


def create_open_question(connection: sqlite3.Connection, payload: OpenQuestionCreate):
    _require_project(connection, payload.project_id)
    if payload.related_claim_id is not None:
        ctx = AccessContext(
            user_id="local", project_id=payload.project_id, conversation_id=None,
            branch_id=None, agent_id=None,
        )
        _require_visible(connection, ctx, "claim", payload.related_claim_id)
    with connection:
        question_id = epistemic_repo.create_open_question(
            connection, project_id=payload.project_id, text=payload.text,
            related_claim_id=payload.related_claim_id,
        )
    return epistemic_repo.get_open_question(connection, question_id)


def list_open_questions(connection: sqlite3.Connection, ctx: AccessContext,
                        state: str | None = None, limit: int = 50, offset: int = 0):
    return epistemic_repo.list_open_questions(
        connection, ctx.project_id, state, limit, offset
    )


def update_open_question(connection: sqlite3.Connection, question_id: str,
                         payload: OpenQuestionUpdate, ctx: AccessContext):
    _require_visible(connection, ctx, "open_question", question_id)
    current = epistemic_repo.get_open_question(connection, question_id)
    if current is None:
        raise ResourceNotFound("Open question not found.")
    transitions = {
        "open": {"investigating", "answered", "dropped"},
        "investigating": {"open", "answered", "dropped"},
        "answered": set(),
        "dropped": set(),
    }
    if payload.state != current["state"] and payload.state not in transitions[str(current["state"])]:
        raise InvalidEpistemicRecord("Invalid open-question state transition.")
    with connection:
        return epistemic_repo.update_open_question(connection, question_id, payload.state)
