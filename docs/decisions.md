# Decisions

This is the project's living decision log. Add concise entries when an implementation choice resolves an ambiguity or departs from the build specification.

## Initial implementation decisions

- **Workflow:** Adopted Development State Machine Workflow 1.6.0 as recorded in Build-spec.md; follow the current canonical workflow (1.6.1 at implementation start) unless explicitly pinned. Use Testing and Verification and Context Continuity modules.
- **ASGI server:** Add Uvicorn as a runtime dependency because FastAPI is an ASGI application and needs an ASGI server to run outside tests.
- **Test client:** Use HTTPX2 as a development dependency because current Starlette TestClient uses it; plain HTTPX is deprecated by Starlette.
- **Package build backend:** Use Setuptools as the PEP 517 build backend so the src/ package can be installed by uv; it is a build-time dependency only.
- **Local API token:** Require COGPLAT_API_TOKEN; Electron will generate and pass a fresh token in M8.
- **Data directory:** Resolve COGPLAT_DATA_DIR first, otherwise use the platform's standard per-user application-data location and append CognitivePlatform.
- **Migrations:** Apply numbered SQL migrations transactionally and record each applied version.
- **API documentation:** Disable FastAPI's default unprotected documentation routes and expose OpenAPI only at authenticated /v1/openapi.json.
- **Existing design filename:** Preserve Build-spec.md; do not create a duplicate BUILD_SPEC.md.

## M1 decisions

- **UUIDv7:** Implement UUIDv7 generation using Python's standard-library uuid.UUID and secrets, because Python 3.12 does not provide uuid.uuid7(). This avoids adding a dependency and keeps ID generation in Python.
- **Branching from inherited history:** A branch may be forked from any message visible in the selected parent branch, including a message inherited from an ancestor. History resolution therefore follows the message's owning branch through the ancestry chain instead of assuming the fork message belongs to the immediate parent branch. This preserves the documented fork-at-any-message behavior and correctly handles fork-of-fork cases.
- **Message API:** Add POST /v1/branches/{branch_id}/messages as the M1 append-only message endpoint. The build spec requires message persistence and branch history but does not name a standalone message route; this endpoint is the smallest direct API for exercising that capability before chat streaming arrives in M2.
- **Database schema:** M1 uses the existing M0 tables and FTS triggers; no schema migration is needed.

## M2 decisions

- **Provider HTTP transport:** Use Python's standard-library `urllib` with `asyncio.to_thread` for streaming and model discovery. This avoids adding an unlisted runtime HTTP dependency while keeping the adapter interface asynchronous.
- **Provider endpoints:** Configure default Ollama and OpenAI-compatible base URLs through `COGPLAT_OLLAMA_BASE_URL` and `COGPLAT_OPENAI_COMPAT_BASE_URL`; keep provider API keys out of settings and SQLite.
- **Remote API key transport:** Accept a remote provider key only through the per-request `X-Provider-API-Key` header. Do not store it in run records, provider configuration, or logs.
- **M2 remote opt-in boundary:** Reject remote chat requests unless `allow_remote=true`. The complete deterministic remote gate, memory-scope filtering, and transmission audit are intentionally M3 work.
- **Run persistence:** Reuse the existing `runs` and `run_steps` tables from migration 0001; M2 requires no schema migration.
- **Provider configuration scope:** M2 exposes provider listing and model discovery for environment-configured providers. Persistent provider creation via `POST /v1/providers` is deferred rather than adding a partial configuration store.


## M3 decisions

- **Audit byte count:** UTF-8 byte length of compact JSON role/content messages at the provider-adapter boundary; excludes HTTP headers and provider/model envelope fields.
- **Audit ordering:** Commit the transmission ledger row before invoking the provider stream. Failed provider calls remain auditable because a request may already have reached the provider.
- **Append-only enforcement:** SQLite triggers reject updates and deletes from `remote_transmissions`; M3 adds migration 0002 rather than recreating the M0 table.
- **Memory scope timing:** Global/user filtering is a deterministic helper with opt-in settings defaulting false. M5 must call it when the context compiler begins adding memory to chat packets; M3 has no memory context compiler to wire yet.
- **Audit API:** Add authenticated `GET /v1/transmissions`; pagination and UI presentation are deferred.


## M4 decisions

- Memory content is immutable after creation. A changed belief or preference is represented by a new item, then the prior item is marked superseded with a same-scope superseded_by reference. Outdated and archived states preserve the original record; there is no hard-delete endpoint.
- Branch memory visibility walks from the requested branch toward the root. Each ancestor's memory is eligible only when created_at is at or before the fork-message timestamp for the edge leading to that ancestor. Each fork-of-fork edge has its own cutoff.
- The current backend has one local user and no account system. User memory therefore uses a NULL scope_id; AccessContext.user_id is a stable local placeholder until multi-user support is in scope.
- M4 exposes FTS5 search through GET /v1/memory?q=..., restricted by the same scope-eligibility predicate as list and detail reads. FTS terms are quoted and OR-combined to avoid interpreting raw input as FTS operators.
- Migration 0003 enforces scope-id shape and same-scope active replacement links. Entity existence and branch ancestry remain deterministic service-level checks.

## M6 decisions

- **Canonical records:** Reuse the epistemic tables created by migration 0001; do not rewrite an applied migration. Add a new migration only for missing indexes, FTS synchronization, or database-enforced invariants.
- **Scope:** Claims and sources use their existing nullable `project_id`: NULL means globally visible; a project-bound record is visible only when the request's validated project matches. A conversation or branch does not create a second claim scope in M6.
- **Status projection:** Status events remain append-only and are keyed by `(claim_id, scope)`. The current projection is the newest event per scope, ordered by `created_at DESC, id DESC`; context for a project includes `default` and that project's `project:<id>` status when present.
- **Initial status:** A user-originated claim starts as `reported`; agent- or extraction-originated claims start as `proposed`; imported claims start as `unknown`. Each is represented by an ordinary status event, not a column on `claims`. When `origin_ref` is supplied, the service validates the canonical target and project visibility, then records a `claim -> origin` `derived_from` link.
- **Immutable epistemic history:** Claims, sources, status events, assessments, evidence, and claim relations are append-only. Open-question state is the exception: it follows the existing explicit state field and can be changed through its API.
- **Assessments:** Store independent assessment dimensions; never combine them into one confidence value. The claim response projects the latest assessment per dimension while the database retains every assessment event.
- **Contradictions:** A contradiction is a directional relation record, not a mutation of either claim. When a selected claim is contested, context compilation includes its visible contradicting partner as a bundle; the partner's own status remains independent.
- **Source handling:** M6 registers source metadata and content hashes and stores evidence excerpts/locators. It does not fetch URLs, crawl websites, or ingest arbitrary files; those are separate import/retrieval capabilities.
- **Context selection:** Add relevant claims by deterministic FTS match against the current user message. Include current scoped status and a contested claim's visible contradiction partner together; include whole claim records only, record budget exclusions, and preserve M5's final packet budget invariant.
- **Remote use:** Claims follow the existing project visibility rule and the explicit per-turn remote gate. M6 adds no separate claim-sharing toggle; every remote transmission remains covered by M3 audit.
- **Unified search:** `GET /v1/search` returns permission-filtered messages, active memory, and claims. Message search requires a branch context and uses resolved branch history; `scope` filters memory scope only. Source metadata is not full-text indexed in M6.
- **Scope boundary:** No argument/premise graph, automated truth judgment, model-based claim extraction, background curation, graph database, or LangGraph work in M6. Model extraction remains M7 and must create proposed records with provenance.

