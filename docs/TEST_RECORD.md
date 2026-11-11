# Test Record

## Latest accepted candidate

- **Candidate:** backend 0.1.0 (M1 — Conversations and branching)
- **Implementation commit:** b278b3b9c2e70b35ab76f4ed27ee8c1c3e706c00
- **Accepted tag:** `backend-v0.1.0`
- **Tag target:** 263c07c1568060a6cd44d1fb144cf06d5fb9601d (documentation follow-up commit; tested M1 code unchanged)
- **Run date:** 2026-11-11
- **CI environment:** GitHub Actions, Ubuntu 26.04, Python 3.12.16, pytest 9.2.0.
- **Workflow run:** [Backend CI #7](https://github.com/KRMRGold/SMH-Tree/actions/runs/43107739858)
- **CI command:** uv sync --dev; uv run pytest
- **CI result:** PASS — 30 passed in 1.07s.
- **Additional local run:** User-reported Windows `win32`, Python 3.12.13; `uv run pytest`; PASS — 30 passed in 3.39s. The exact local checkout SHA was not captured, so this is recorded as user-reported verification rather than independently commit-attributed evidence.
- **Candidate status:** ACCEPTED — M1 acceptance criteria passed and required tag created.

## M1 acceptance checks

| Check | Result | Evidence |
|---|---|---|
| Existing M0 regression suite | PASS | All 15 M0 tests remain green in the 30-test CI run |
| UUIDv7 generation | PASS | 100 generated IDs parse as UUIDv7 and are unique |
| Linear history | PASS | Messages resolve in per-branch sequence order |
| Fork cutoff | PASS | Child inherits only through its fork message |
| Parent messages after fork | PASS | Later parent messages do not appear in child history |
| Sibling isolation | PASS | Sibling-only messages remain isolated |
| Fork of a fork | PASS | Root, child, and grandchild history resolves in chronological order |
| Fork at inherited ancestor message | PASS | Earlier ancestor target excludes intermediate branch messages |
| Invalid fork target | PASS | Service rejects a message not visible in selected parent branch |
| Deep ancestry | PASS | 50-level branch chain resolves all 51 messages without recursion |
| Sequence uniqueness | PASS | Duplicate per-branch seq rejected by SQLite unique constraint |
| Project and conversation creation | PASS | Project association and root branch creation verified |
| Missing project | PASS | Conversation creation rejected; no orphan conversation created |
| API project/conversation/branch/message flow | PASS | FastAPI TestClient integration flow succeeds |
| API auth on new routes | PASS | Missing bearer token returns 401 |
| Candidate tag | PASS | `backend-v0.1.0` exists and points to the documentation follow-up commit 263c07c1568060a6cd44d1fb144cf06d5fb9601d |

## Source inspection

- Inspected the M1 commit diff for API routes, repositories, service logic, domain contracts, and tests.
- Branch history resolution explicitly handles a fork target on an ancestor branch, rather than assuming the target belongs to the immediate parent.
- Message sequence allocation uses one INSERT...SELECT statement, with the database unique constraint as the final invariant.
- No schema migration or new third-party dependency was needed.

## M0 accepted baseline

- **Backend:** 0.0.3
- **Source commit:** 7795b2f2fe68594d713cfe30088d555c03673899
- **CI:** [Backend CI #4](https://github.com/KRMRGold/SMH-Tree/actions/runs/43106530591)
- **Result:** PASS — 15 tests on Python 3.12.16.
- **Tag exception:** User explicitly accepted proceeding without backend-v0.0.3. This exception applies to M0 only.

## Earlier M0 candidate history

| Candidate | Commit | Result |
|---|---|---|
| backend 0.0.1 | d39dfc21fa51a9c69d8a497cb454c717306e0b6f | 15 passed on Python 3.12; Starlette deprecation warning for plain HTTPX |
| backend 0.0.2 | 4affe726f5046f53f085685bc48d35e7f56a2ce7 | FAILED: 14 passed, 1 failed due to stale version assertion |
| backend 0.0.3 | 7795b2f2fe68594d713cfe30088d555c03673899 | 15 passed on Python 3.12; no deprecation warning |

Failed and superseded candidates remain in Git history; their version identities are not reused.

## Not run

- Windows-specific runtime checks were deferred for M1; user-run Windows test suite now passes, but clean-machine packaging remains M9.
- Ollama, remote-provider, chat-streaming, desktop, and end-to-end checks are not M1 scope.
