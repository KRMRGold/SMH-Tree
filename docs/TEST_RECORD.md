# Test Record

## Latest candidate run

- **Candidate:** backend 0.1.0 (M1 — Conversations and branching)
- **Candidate commit:** b278b3b9c2e70b35ab76f4ed27ee8c1c3e706c00
- **Run date:** 2026-11-11
- **Environment:** GitHub Actions, Ubuntu 26.04, Python 3.12.16, pytest 9.2.0.
- **Workflow run:** [Backend CI #7](https://github.com/KRMRGold/SMH-Tree/actions/runs/43107739858)
- **Command:** uv sync --dev; uv run pytest
- **Result:** PASS — 30 passed in 1.07s.
- **Candidate status:** Tests pass; M1 acceptance is pending the required backend-v0.1.0 Git tag or an explicit user-approved exception.

## M1 acceptance checks

| Check | Result | Evidence |
|---|---|---|
| Existing M0 regression suite | PASS | All 15 M0 tests remain green in the 30-test run |
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

## Source inspection

- Inspected the M1 commit diff for API routes, repositories, service logic, domain contracts, and tests.
- Branch history resolution explicitly handles a fork target on an ancestor branch, rather than assuming the target belongs to the immediate parent.
- Message sequence allocation uses one INSERT...SELECT statement, with the database unique constraint as the final invariant.
- No schema migration or new third-party dependency was needed.

## Acceptance status and remaining workflow item

- **M1 functional acceptance tests:** PASS.
- **Python 3.12 CI:** PASS for the exact candidate commit.
- **Candidate Git tag:** BLOCKED — the connected GitHub integration does not expose tag creation. Create backend-v0.1.0 pointing to b278b3b9c2e70b35ab76f4ed27ee8c1c3e706c00, or explicitly accept proceeding without the tag.
- **M1 overall:** Candidate, not formally accepted yet.

## M0 accepted baseline

- **Backend:** 0.0.3
- **Source commit:** 7795b2f2fe68594d713cfe30088d555c03673899
- **CI:** [Backend CI #4](https://github.com/KRMRGold/SMH-Tree/actions/runs/43106530591)
- **Result:** PASS — 15 tests on Python 3.12.16.
- **Tag exception:** User explicitly accepted proceeding without backend-v0.0.3. This exception applies to M0 only; M1 still requires its tag unless separately waived.

## Earlier M0 candidate history

| Candidate | Commit | Result |
|---|---|---|
| backend 0.0.1 | d39dfc21fa51a9c69d8a497cb454c717306e0b6f | 15 passed on Python 3.12; Starlette deprecation warning for plain HTTPX |
| backend 0.0.2 | 4affe726f5046f53f085685bc48d35e7f56a2ce7 | FAILED: 14 passed, 1 failed due to stale version assertion |
| backend 0.0.3 | 7795b2f2fe68594d713cfe30088d555c03673899 | 15 passed on Python 3.12; no deprecation warning |

Failed and superseded candidates remain in Git history; their version identities are not reused.

## Not run

- Windows-specific runtime checks are deferred; the desktop shell and Windows packaging are later milestones.
- Ollama, remote-provider, chat-streaming, desktop, and end-to-end checks are not M1 scope.
