# Test Record

## Latest candidate run

- **Candidate:** backend 0.0.3
- **Candidate commit:** `7795b2f2fe68594d713cfe30088d555c03673899`
- **Run date:** 2026-11-11
- **Environment:** GitHub Actions, Ubuntu 26.04, Python 3.12.16, pytest 9.2.0.
- **Workflow run:** [Backend CI #4](https://github.com/KRMRGold/SMH-Tree/actions/runs/43106530591)
- **Candidate status:** Candidate — all M0 tests pass; acceptance is pending the required Git tag.

## Executed checks for backend 0.0.3

| Check | Result | Evidence |
|---|---|---|
| Backend test suite | PASS | CI run 4 on the exact candidate commit — 15 passed in 0.77s |
| Python 3.12 target runtime | PASS | CI setup and test log report Python 3.12.16 |
| Dependency installation | PASS | `uv sync --dev` completed successfully in CI |
| Test-client deprecation | PASS | CI test log contains no Starlette/httpx deprecation warning after switching to HTTPX2 |
| API authentication | PASS | Health and OpenAPI tests cover missing, invalid, and valid bearer tokens |
| Migration idempotency | PASS | Migration 0001 applies once; repeated application leaves its record unchanged |
| Section 4 schema inventory | PASS | All 22 specified tables, including both FTS virtual tables, exist |
| Foreign-key enforcement | PASS | Per-connection pragma is enabled; invalid branch reference raises IntegrityError |
| SQLite WAL | PASS | Connection reports journal mode `wal` |
| FTS synchronization | PASS | Inserted message and memory content are searchable through their FTS tables |
| Data-directory resolution | PASS | Override and Windows, macOS, and Linux resolution cases are tested |

## Earlier candidate history

| Candidate | Commit | Result |
|---|---|---|
| backend 0.0.1 | `d39dfc21fa51a9c69d8a497cb454c717306e0b6f` | 15 passed on Python 3.12; one Starlette deprecation warning because the test setup used plain HTTPX |
| backend 0.0.2 | `4affe726f5046f53f085685bc48d35e7f56a2ce7` | FAILED: 14 passed, 1 failed. The health test still expected version 0.0.1 after the package version had been bumped to 0.0.2 |
| backend 0.0.3 | `7795b2f2fe68594d713cfe30088d555c03673899` | 15 passed on Python 3.12 with no deprecation warning |

Failed and superseded candidates remain in Git history; their version identities are not reused.

## Remaining workflow item

| Item | Result | Reason / minimum action |
|---|---|---|
| Candidate Git tag | BLOCKED | The connected GitHub integration does not expose a tag-creation action. Create `backend-v0.0.3` pointing to commit `7795b2f2fe68594d713cfe30088d555c03673899`, or explicitly accept proceeding without the tag. |

## Not run

- Windows-specific runtime checks are deferred; the desktop shell and Windows packaging are later milestones.
- Desktop, Ollama, remote-provider, and end-to-end checks are not M0 scope.

## Acceptance decision

**M0 is test-passing but not yet formally accepted.** The complete M0 test suite passed on the specified Python 3.12 runtime for the exact backend 0.0.3 commit. Do not begin M1 until the required candidate tag is created or the user explicitly accepts that documented workflow limitation.
