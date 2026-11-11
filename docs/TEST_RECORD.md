# Test Record

## Latest candidate run

- **Candidate:** backend 0.0.1
- **Candidate commit:** `d39dfc21fa51a9c69d8a497cb454c717306e0b6f`
- **Run date:** 2026-11-11
- **Environment:** Linux; Python 3.13.5; SQLite 3.46.1 with FTS5; FastAPI 0.128.2; Pydantic 2.13.5; pytest 9.0.2.
- **Candidate status:** Candidate — M0 is not yet accepted.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Backend tests | PASS | `PYTHONPATH=src python -m pytest -q` — 15 passed |
| Python compilation | PASS | `python -m compileall -q src tests` |
| Git whitespace check | PASS | `git diff --cached --check` |
| Authenticated health endpoint | PASS | TestClient: valid bearer token returns 200; missing/invalid token returns 401 |
| Authenticated OpenAPI endpoint | PASS | Missing token returns 401; valid token returns 200 |
| Migration idempotency | PASS | Migration 0001 applies once; repeated application leaves its record unchanged |
| Section 4 schema inventory | PASS | All 22 specified tables, including both FTS virtual tables, exist |
| Foreign-key enforcement | PASS | Per-connection pragma is enabled; invalid branch reference raises IntegrityError |
| SQLite WAL | PASS | Connection reports journal mode `wal` |
| FTS synchronization | PASS | Inserted message and memory content are searchable through their FTS tables |

## Blocked or unverified checks

| Check | Result | Reason / minimum action |
|---|---|---|
| Python 3.12 target runtime | BLOCKED | This environment has Python 3.13.5 only. Run the suite under Python 3.12 or obtain a successful Python 3.12 CI run. |
| GitHub Actions CI for candidate commit | BLOCKED | No workflow run or check status was visible for the candidate commit when inspected. Enable/trigger Actions or run the workflow manually, then record its result. |
| uv dependency lock generation in this environment | BLOCKED | Offline resolution had no Python 3.12 interpreter and no cached FastAPI package. The CI workflow uses the official uv setup action and will resolve dependencies online. |
| Candidate Git tag | BLOCKED | The connected GitHub integration does not expose a tag-creation action. Create `backend-v0.0.1` pointing to the candidate commit after verification. |

## Not run

- Windows-specific runtime checks are deferred; the desktop shell and Windows packaging are later milestones.
- Desktop, Ollama, remote-provider, and end-to-end checks are not M0 scope.

## Acceptance decision

**M0 remains a candidate, not accepted.** All 15 tests passed in the available Python 3.13.5 environment, but the specified Python 3.12 target and GitHub Actions execution have not been verified. Do not begin M1 until the blocked verification is resolved or the user explicitly accepts the documented limitation.
