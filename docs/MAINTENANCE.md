# Maintenance

## Current accepted state

- **Project:** SMH-Tree
- **Last accepted backend version:** 0.7.0 (M7 — Checkpointed workflows and explicit claim extraction)
- **M5 implementation commit:** fdf74b171d0ff838db29002df5f38ac0dbe3b7b5
- **M5 candidate verification commit and release tag target:** 31ad365f2a94bbe69bed5772dd34449c5fd758ec (`backend-v0.5.0`)
- **M5 acceptance:** Accepted on 2026-11-12 after CI, user-reported Windows verification, and independent GitHub verification of the annotated `backend-v0.5.0` tag target. The tag points to `31ad365f2a94bbe69bed5772dd34449c5fd758ec`.
- **M6 acceptance:** Accepted on 2026-11-12 after CI (77 passed), user-reported Windows verification (all tests passed), and independent verification of both annotated tag targets. `backend-v0.6.0` points to failed candidate `d99a52e014e2471fe14e2e65892163871f810f42`; `backend-v0.6.1` points to passing candidate `0f3b8bdf0a321fb20a9f41f6797812e648b73187`.
- **M7 acceptance:** Accepted on 2026-11-12 after CI (83 passed), user-reported Windows verification (all 83 passed), and independent verification of annotated tag `backend-v0.7.0` pointing to `9d525efd333812abdbca17e1a22efff610f063d0`.
- **Failed-candidate tag:** `backend-v0.4.0` → 41ae1363fd2ceb79fa9e117b1d237d4db526dc84.
- **Accepted tag:** `backend-v0.4.1` → f4c6e9ad7bdee58623f60a0e5c3186b5b687d5a5.
- **M2 acceptance:** Accepted on 2026-11-11. Both `backend-v0.2.0` (failed candidate) and `backend-v0.2.1` (passing candidate) were created and independently verified against their exact commit targets.
- **M0 acceptance:** Accepted on 2026-11-11. The user explicitly chose to proceed without creating the required backend-v0.0.3 Git tag. This is a documented workflow exception, not a claim that the tag exists.
- **M1 acceptance:** Accepted on 2026-11-11. The required backend-v0.1.0 tag was created and verified. It points to 263c07c1568060a6cd44d1fb144cf06d5fb9601d, a documentation follow-up commit whose code tree retains the tested M1 implementation from b278b3b9c2e70b35ab76f4ed27ee8c1c3e706c00.
- **Workflow:** [Development State Machine Workflow](https://github.com/KRMRGold/Meta-Modules/blob/main/workflows/Development-State-Machine-Workflow.md), current canonical version 1.6.1. Project adoption provenance remains 1.6.0 as recorded in Build-spec.md.
- **Testing module:** Testing and Verification 0.1.2.
- **Continuity module:** Context Continuity 0.1.2.


## M3 — Remote gate and audit (accepted)

- **Failed candidate:** backend 0.3.0 (CI run 43113745788; 43 passed, 1 failed because the idempotency test retained the old schema-version expectation).
- **Accepted backend version:** 0.3.1
- **Implementation/tag commit:** c61c8a9398e3ce008c40da25a647806827e1df7a
- **Accepted tag:** `backend-v0.3.1` (verified against the exact commit above).
- **Failed-candidate tag:** `backend-v0.3.0` → 0d106009302e235cec68850b0a1c52892eb9bc34 (verified).
- **CI:** [Backend CI #14](https://github.com/KRMRGold/SMH-Tree/actions/runs/43113953986), Python 3.12.16, 44 passed in 2.30s.
- **Scope:** deterministic remote-transmission gate, global/user memory filtering policy, and append-only transmission audit.
- **Windows verification:** User-reported `uv run pytest`, Windows `win32`, Python 3.12.13, 44 passed in 6.23s.
- **Acceptance:** Accepted on 2026-11-11 after CI, Windows verification, and both tag targets were verified.
- **Schema:** Migration 0002 adds database-enforced update/delete rejection for the existing `remote_transmissions` ledger.

## Implemented behavior

### M0 — Skeleton (accepted)

- Python 3.12+ backend package managed with uv.
- FastAPI application factory with bearer-token authentication on all exposed endpoints.
- Authenticated health and OpenAPI endpoints; default public docs routes disabled.
- Platform-aware application-data directory resolution, with COGPLAT_DATA_DIR override.
- SQLite connection configured for foreign keys, WAL, and busy timeout.
- Transactional numbered SQL migration runner.
- Initial schema for projects, conversations, branches, messages, FTS5, memory, epistemic records, links, runs, provider configuration, context snapshots, transmission audit, and settings.
- FTS5 synchronization triggers for messages and memory.
- Verification: [Backend CI #4](https://github.com/KRMRGold/SMH-Tree/actions/runs/43106530591), Python 3.12.16, 15 tests passed.

### M1 — Conversations and branching (accepted)

- Create and list projects.
- Create and list conversations; creation atomically creates a root Main branch.
- List branches in a conversation.
- Append immutable messages to a branch with per-branch sequence numbers.
- Fork a branch at any message visible in its parent branch, including messages inherited from more distant ancestors.
- Resolve branch history without copying messages; parent messages after the fork and sibling messages are excluded.
- UUIDv7 IDs and UTC ISO-8601 timestamps are generated in Python.
- API endpoints are authenticated and use the standard error envelope for explicit HTTP errors.
- Verification: [Backend CI #7](https://github.com/KRMRGold/SMH-Tree/actions/runs/43107739858), exact implementation candidate commit b278b3b9c2e70b35ab76f4ed27ee8c1c3e706c00, Python 3.12.16, 30 tests passed.
- Tag: `backend-v0.1.0` points to 263c07c1568060a6cd44d1fb144cf06d5fb9601d, the documentation follow-up commit containing the same tested M1 code.
- Additional user-run verification: Windows 10/11 environment (`win32`), Python 3.12.13, `uv run pytest` — 30 passed in 3.39s. Reported by the user; the exact local checkout SHA was not independently captured in this session.

### M2 — Provider layer and chat streaming (accepted)

- Added the `ModelProvider` protocol and standard-library HTTP streaming helpers.
- Added Ollama newline-delimited JSON streaming and OpenAI-compatible SSE streaming adapters.
- Added environment-configurable provider base URLs: `COGPLAT_OLLAMA_BASE_URL` and `COGPLAT_OPENAI_COMPAT_BASE_URL`.
- Added authenticated provider listing and model discovery endpoints.
- Added authenticated `POST /v1/branches/{branch_id}/chat` SSE endpoint with ordered token events, completion event, and provider-error event.
- Chat runs and ordered run steps are persisted in the existing M0 schema; no migration was required.
- User messages are persisted before generation. The assistant response is persisted exactly once only after successful completion. Provider failures mark the run failed; cancellation marks it cancelled and does not persist partial assistant output.
- Remote provider requests are rejected unless `allow_remote=true` is explicitly supplied. Remote API keys are accepted through the per-request `X-Provider-API-Key` header and are not written to SQLite or run records.

- Verification: [Backend CI #12](https://github.com/KRMRGold/SMH-Tree/actions/runs/43111577117), implementation commit ee757c186acf20d31d3fcc0b5a20292cd80ee530, Python 3.12.16, 38 tests passed in 2.42s.
- Additional user-run verification: Windows (`win32`), Python 3.12.13, `uv run pytest` — 38 passed in 5.71s, reported by the user on the updated checkout.
- Tags: `backend-v0.2.0` points to failed candidate e1eb64313d312c530b866ddfca8eda59dc9391ce; `backend-v0.2.1` points to a6dd5a9808a9ea235befbd205a45fe70baf56067, the documentation follow-up commit containing the tested M2 implementation. Both refs were verified on GitHub.
- Provider configuration is currently environment-based; persistent provider creation via `POST /v1/providers` remains deferred.

### M3 implemented behavior

- Remote-provider transmission authorization is enforced in the chat service immediately before provider invocation; remote calls fail closed unless the run explicitly opts in.
- Each allowed remote request writes a durable audit record before provider network I/O. The record includes provider label, run ID, referenced message IDs, UTF-8 byte count of the compact role/content packet, and timestamp.
- Authenticated `GET /v1/transmissions` lists the audit records.
- Migration 0002 adds SQLite triggers that reject updates and deletes from `remote_transmissions`.
- Global and user memory are excluded by default by the deterministic remote-memory permission helper. Explicit per-scope settings enable sharing; the context compiler integration remains M5 work.
- Verification: [Backend CI #14](https://github.com/KRMRGold/SMH-Tree/actions/runs/43113953986), implementation/tag commit c61c8a9398e3ce008c40da25a647806827e1df7a, Python 3.12.16, 44 tests passed in 2.30s.
- Additional user-run verification: Windows (`win32`), Python 3.12.13, `uv run pytest` — 44 passed in 6.23s.
- Tags: `backend-v0.3.0` points to failed candidate 0d106009302e235cec68850b0a1c52892eb9bc34; `backend-v0.3.1` points to accepted candidate c61c8a9398e3ce008c40da25a647806827e1df7a. Both refs were independently fetched from GitHub and matched exact targets.

### M4 — Scoped memory (accepted)

- **Accepted backend version:** 0.4.1.
- **Implementation commit:** 0cfbbcc0d34a74264628a15f76275fe115ce787f.
- **Accepted documentation commit / tag target:** f4c6e9ad7bdee58623f60a0e5c3186b5b687d5a5.
- **Accepted tag:** `backend-v0.4.1`.
- **Failed-candidate tag:** `backend-v0.4.0` → 41ae1363fd2ceb79fa9e117b1d237d4db526dc84.
- **CI:** PASS — [Backend CI #15](https://github.com/KRMRGold/SMH-Tree/actions/runs/43116317844), Python 3.12.16, pytest 9.2.0, 55 passed in 3.15s.
- **Windows verification:** PASS — user-reported Windows (`win32`), Python 3.12.13, `uv run pytest`, 55 passed in 6.87s.
- **Tag evidence:** User confirmed both tags were pushed; prior session reported tag targets verified. The current connector cannot independently enumerate tag refs, so this record distinguishes that prior verification from a fresh check in this session.
- **Behavior:** authenticated scoped memory create/list/detail/lifecycle API under /v1/memory; global/user/project/conversation/branch/agent scopes; deterministic eligibility through branch ancestry with fork-time cutoffs and sibling exclusion; FTS5 search with scope/state filtering; immutable memory content with outdated, superseded, and archived lifecycle states; no hard-delete endpoint.
- **Schema:** migration 0003 enforces scope-id shape and same-scope active supersession links at the database boundary.
- **Acceptance:** ACCEPTED — CI, user-reported Windows verification, and release-tag completion have been recorded.

### M5 — Context compiler and inspector (accepted)

- **Candidate backend version:** 0.5.0.
- **Implementation commit:** fdf74b171d0ff838db29002df5f38ac0dbe3b7b5.
- **Latest candidate verification commit:** 31ad365f2a94bbe69bed5772dd34449c5fd758ec.
- **CI:** PASS — [Backend CI #64](https://github.com/KRMRGold/SMH-Tree/actions/runs/43131791949), Python 3.12.16, pytest 9.2.0, 64 passed in 2.98s. The run followed the candidate verification commit; it verifies the unchanged implementation plus documentation updates.
- **Windows verification:** PASS — user-reported `uv run pytest`, Windows 11 environment (`win32`), Python 3.12.13, pytest 9.2.0, 64 passed in 9.69s.
- **Accepted release tag:** Annotated tag `backend-v0.5.0` points to `31ad365f2a94bbe69bed5772dd34449c5fd758ec`. GitHub ref and annotated-tag object were fetched and independently checked.
- **Implemented:** deterministic provider-neutral context compilation; fixed mandatory system instructions; project description context; M4-scoped active memory with FTS relevance, importance/preference inclusion, stable ordering and remote-sharing filtering; M1 branch history selection; head-and-tail current-message truncation; token budgeting and omission metadata; immutable one-per-run snapshots via migration 0004; authenticated stored-packet inspector at `GET /v1/runs/{id}/context`.
- **Run lifecycle:** context compilation and provider streaming are separate run steps. A successfully compiled packet is snapshotted before remote authorization/audit and before provider I/O; snapshots remain after provider failure or cancellation.
- **Deferred:** epistemic sources (M6), model-specific context profiles, model-based ranking, embeddings, vector search, background memory curation, agents and LangGraph (M7).
- **Acceptance:** ACCEPTED on 2026-11-12 — implementation, CI, user-reported Windows verification, and release tag verified.

### M6 — Epistemic records and claim-aware context (accepted)

- **Current candidate version:** 0.6.1.
- **Failed candidate version:** 0.6.0; latest failed candidate commit `d99a52e014e2471fe14e2e65892163871f810f42` (CI run #43285511530 failed because same-second event timestamps plus random UUID ordering selected the wrong latest status/assessment).
- **Candidate verification commit:** `0f3b8bdf0a321fb20a9f41f6797812e648b73187`.
- **CI:** PASS — [Backend CI #43285806228](https://github.com/KRMRGold/SMH-Tree/actions/runs/43285806228), Python 3.12, 77 passed in 4.94s.
- **Windows verification:** PASS — user-reported Windows `uv run pytest`; all tests passed on the updated `main` checkout.
- **Failed-candidate tag:** `backend-v0.6.0` verified as an annotated tag pointing to `d99a52e014e2471fe14e2e65892163871f810f42`.
- **Accepted release tag:** `backend-v0.6.1` verified as an annotated tag pointing to `0f3b8bdf0a321fb20a9f41f6797812e648b73187`.
- **Acceptance:** ACCEPTED on 2026-11-12 — CI, user-reported Windows verification, and both tag targets verified.
- **Implemented:** source registration with metadata/hash validation; immutable claims and source records; provenance `derived_from` links; append-only scoped status events, assessments, evidence, and relations; per-dimension assessment projection; project/global visibility; contradiction relations and contested-partner context bundles; open-question state transitions; claim FTS; unified search over claims, active memory, and branch-visible messages; claim-aware context compilation with a 20% claim budget.
- **Migration:** 0005 adds claim FTS, search/scope indexes, and database-enforced append-only invariants. Existing migration 0001 was not rewritten.

### M7 — Checkpointed workflows and explicit claim extraction (accepted)

- **Accepted backend version:** 0.7.0.
- **Candidate implementation and annotated tag target:** `9d525efd333812abdbca17e1a22efff610f063d0`.
- **Accepted tag:** `backend-v0.7.0`; its GitHub ref resolves to an annotated tag object whose target is the exact candidate commit.
- **CI:** PASS — [Backend CI #157](https://github.com/KRMRGold/SMH-Tree/actions/runs/43291634423), Python 3.12.16, pytest 9.2.0, 83 passed in 6.35s.
- **Windows verification:** PASS — user-reported Windows `uv run pytest`, all 83 tests passed. The local checkout was `45175c2713f6edcb95833238a24cc70167c84a0f`, two documentation-only commits ahead of the tested candidate; GitHub comparison confirmed no application-code changes between them.
- **Implemented:** checkpointed LangGraph chat lifecycle; authenticated workflow resume; explicit claim extraction endpoint; strict provider-independent structured-output and exact-evidence validation; proposed claims with evidence and provenance links; remote extraction opt-in; feature-flag fallback to the existing chat path.
- **Persistence:** migration 0006 stores remote packet SHA-256 and enforces one audit row per run. Canonical product data remains in `app.db`; LangGraph checkpoints use a separate `checkpoints.db` to avoid SQLite lock contention.
- **Deferred:** argument/premise graphs, automated truth judgment, confidence scores, autonomous/background curation, graph database, vector search, and multi-agent orchestration.
- **Acceptance:** ACCEPTED on 2026-11-12 — CI, user-reported Windows verification, and annotated release tag independently verified.

## Architecture and invariants

- SQLite is the canonical store; no ORM.
- IDs and timestamps are generated by Python, not SQLite.
- Branch messages are append-only. Forking stores a parent branch and fork-message reference; it does not copy history.
- A branch's visible history is its own messages plus the inherited ancestry path ending at its fork message. A fork may target a message inherited from an ancestor; intermediate branches contribute no later messages.
- Sibling messages and parent messages appended after a fork are excluded.
- Per-branch message sequence uniqueness is enforced by SQLite. Appending obtains the next sequence in one INSERT...SELECT statement to avoid a read-then-write race.
- Every API route requires the per-launch bearer token.
- API is intended to bind to loopback only; desktop process supervision is not implemented until M8.

## Known limitations

- The M2 provider registry uses environment-configured endpoints; persistent provider configuration via POST /v1/providers remains deferred.
- M4 memory services, scope enforcement, FTS search, and lifecycle are accepted in backend 0.4.1. M5 context compiler and inspector are accepted in backend 0.5.0. M6 epistemic records and claim-aware context are accepted in backend 0.6.1. M7 checkpointed workflows and explicit claim extraction are accepted in backend 0.7.0.
- No desktop shell or packaging yet (M8–M9).
- M0's candidate tag was intentionally omitted with user acceptance.
- Windows local tests now pass for the M1 suite; desktop packaging and clean-machine checks remain M9 work.

## Test inventory

| Behavior | Verification |
|---|---|
| API authentication | pytest API integration tests |
| Config and data paths | pytest config unit tests |
| Migration idempotency and schema inventory | pytest database integration tests |
| FK and WAL pragmas | pytest database integration tests |
| Message, memory, and claim FTS triggers | pytest database integration tests |
| Epistemic claim/source/status/evidence/relation append-only invariants | pytest migration tests |
| Claim scope, status projections, assessments, evidence, provenance, and contradictions | pytest epistemic service tests |
| Open-question state transitions and project visibility | pytest epistemic service tests |
| Unified search across claims, memory, and branch-visible messages | pytest search API tests |
| Claim-aware context selection and contested contradiction partners | pytest context compiler tests |
| UUIDv7 generation | pytest domain test |
| Linear branch history | pytest service test |
| Fork cutoff and parent-after-fork exclusion | pytest service tests |
| Sibling isolation | pytest service test |
| Fork-of-fork and inherited-ancestor fork | pytest service tests |
| Depth-50 branch ancestry | pytest service test |
| Per-branch sequence uniqueness | pytest service test |
| Project/conversation creation and scoping | pytest service and API integration tests |
| Authenticated branch/message API | pytest API integration tests |
| Provider protocol, provider listing, and model discovery | pytest chat API tests |
| Ollama NDJSON stream parsing | pytest mocked HTTP server test |
| OpenAI-compatible SSE stream parsing | pytest mocked HTTP server test |
| Chat token ordering and single assistant persistence | pytest SSE integration test |
| Provider failure event and failed run | pytest SSE integration test |
| Cancellation and partial-output suppression | pytest async service test |
| Remote provider denied without explicit opt-in | pytest chat API test |
| Remote audit committed before provider invocation | pytest chat API test with independent DB read |
| Authenticated transmission audit listing | pytest API integration test |
| Transmission audit update/delete rejected | pytest database migration test |
| Global/user memory stripped by default and enabled per scope | pytest remote-gate unit tests |
| Memory scope CRUD and validation | pytest memory API integration tests |
| Memory FTS search and lifecycle transitions | pytest memory service and API tests |
| Project/conversation/agent scope eligibility | pytest memory scope tests |
| Branch ancestry fork-time cutoff and sibling exclusion | pytest memory scope tests, including fork-of-fork |
| Memory scope and supersession database invariants | pytest migration tests |

## Failed candidates

- **backend 0.0.1:** 15 tests passed on Python 3.12, but Starlette emitted a deprecation warning for the plain HTTPX test client.
- **backend 0.0.2:** failed because the health test still expected version 0.0.1 after the version bump; 14 passed, 1 failed.
- **backend 0.0.3:** repaired test-client dependency and version assertion; 15 passed on Python 3.12. Accepted as M0 with the user-approved tag exception.

## Current accepted milestone — M7

- **Accepted version:** backend 0.7.0.
- **Implementation / annotated tag target:** `9d525efd333812abdbca17e1a22efff610f063d0`.
- **Accepted tag:** `backend-v0.7.0` (annotated; tag object independently verified to target the candidate commit).
- **CI:** PASS — Backend CI #157, 83 passed in 6.35s.
- **Windows:** PASS — user-reported `uv run pytest`, all 83 passed on a checkout containing the same application code.
- **Next milestone:** M8 — desktop process supervision and shell integration, subject to the current Build-spec roadmap.

## Current work and next steps

- **Current accepted milestone:** M7 — Checkpointed workflows and explicit claim extraction (backend 0.7.0).
- **M5 decisions:** deterministic compiler; M4 permissions and branch-history resolution reused; current user message is head-and-tail truncated only when mandatory system + user content exceeds budget; system instructions are never truncated; one immutable snapshot per successfully compiled chat run; inspector reads the stored packet rather than recompiling.
- **M6 acceptance complete:** CI, user-run Windows tests, and both annotated release tags are verified.
- **M7 acceptance complete:** backend 0.7.0 is accepted. CI #157 passed 83 tests; user-reported Windows verification passed all 83 tests; annotated `backend-v0.7.0` points to the exact tested candidate commit.
- Keep this file as the single maintenance record; update it in place after each accepted milestone.
