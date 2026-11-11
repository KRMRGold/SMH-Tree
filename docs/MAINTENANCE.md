# Maintenance

## Current accepted state

- **Project:** SMH-Tree
- **Last accepted backend version:** 0.1.0 (M1 — Conversations and branching)
- **Last accepted source commit:** 263c07c1568060a6cd44d1fb144cf06d5fb9601d
- **M0 acceptance:** Accepted on 2026-11-11. The user explicitly chose to proceed without creating the required backend-v0.0.3 Git tag. This is a documented workflow exception, not a claim that the tag exists.
- **M1 acceptance:** Accepted on 2026-11-11. The required backend-v0.1.0 tag was created and verified. It points to 263c07c1568060a6cd44d1fb144cf06d5fb9601d, a documentation follow-up commit whose code tree retains the tested M1 implementation from b278b3b9c2e70b35ab76f4ed27ee8c1c3e706c00.
- **Workflow:** [Development State Machine Workflow](https://github.com/KRMRGold/Meta-Modules/blob/main/workflows/Development-State-Machine-Workflow.md), current canonical version 1.6.1. Project adoption provenance remains 1.6.0 as recorded in Build-spec.md.
- **Testing module:** Testing and Verification 0.1.2.
- **Continuity module:** Context Continuity 0.1.2.

## Current candidate — M2 (not yet accepted)

- **Candidate backend version:** 0.2.1
- **Candidate source commit:** ee757c186acf20d31d3fcc0b5a20292cd80ee530
- **CI:** [Backend CI #12](https://github.com/KRMRGold/SMH-Tree/actions/runs/43111577117) — PASS, 38 tests in 2.42s, Python 3.12.16.
- **Status:** Candidate; automated M2 acceptance tests pass. Formal acceptance is pending the required Git tags. The connected GitHub write actions available in this session cannot create tag refs, so no M2 tag is claimed.
- **Failed candidate:** backend 0.2.0 at e1eb64313d312c530b866ddfca8eda59dc9391ce; CI failed during test collection due to literal newline escape sequences in the provider-model route. The repair is version 0.2.1.

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

### M2 — Provider layer and chat streaming (candidate; automated tests pass)

- Added the `ModelProvider` protocol and standard-library HTTP streaming helpers.
- Added Ollama newline-delimited JSON streaming and OpenAI-compatible SSE streaming adapters.
- Added environment-configurable provider base URLs: `COGPLAT_OLLAMA_BASE_URL` and `COGPLAT_OPENAI_COMPAT_BASE_URL`.
- Added authenticated provider listing and model discovery endpoints.
- Added authenticated `POST /v1/branches/{branch_id}/chat` SSE endpoint with ordered token events, completion event, and provider-error event.
- Chat runs and ordered run steps are persisted in the existing M0 schema; no migration was required.
- User messages are persisted before generation. The assistant response is persisted exactly once only after successful completion. Provider failures mark the run failed; cancellation marks it cancelled and does not persist partial assistant output.
- Remote provider requests are rejected unless `allow_remote=true` is explicitly supplied. Remote API keys are accepted through the per-request `X-Provider-API-Key` header and are not written to SQLite or run records.
- Formal remote transmission policy, scope filtering, and append-only transmission audit remain M3 work.
- Verification: [Backend CI #12](https://github.com/KRMRGold/SMH-Tree/actions/runs/43111577117), candidate ee757c186acf20d31d3fcc0b5a20292cd80ee530, Python 3.12.16, 38 tests passed in 2.42s.
- Provider configuration is currently environment-based; persistent provider creation via `POST /v1/providers` remains deferred.

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

- The last formally accepted backend remains M1 (0.1.0); M2 code is a tested candidate pending tag creation.
- The M2 provider registry uses environment-configured endpoints; persistent provider configuration via POST /v1/providers remains deferred.
- No remote gate and transmission audit service yet (M3).
- No memory services, scope enforcement, context compiler, or epistemic API yet (M4–M6).
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
| Message and memory FTS triggers | pytest database integration tests |
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

## Failed candidates

- **backend 0.0.1:** 15 tests passed on Python 3.12, but Starlette emitted a deprecation warning for the plain HTTPX test client.
- **backend 0.0.2:** failed because the health test still expected version 0.0.1 after the version bump; 14 passed, 1 failed.
- **backend 0.0.3:** repaired test-client dependency and version assertion; 15 passed on Python 3.12. Accepted as M0 with the user-approved tag exception.

## Current work and next steps

- M2 automated acceptance suite passes on candidate backend 0.2.1; formal acceptance is pending the required `backend-v0.2.0` failed-candidate tag and `backend-v0.2.1` passing-candidate tag.
- Run the M2 test suite on the user's Windows checkout and record the exact local result.
- After tag verification, mark M2 accepted and proceed to M3 — remote gate and audit.
- Keep this file as the single maintenance record; update it in place after each accepted milestone.
