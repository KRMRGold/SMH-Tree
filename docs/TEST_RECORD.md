## M6 candidate verification — backend 0.6.1 (not yet accepted)

- **Candidate version:** backend 0.6.1.
- **Failed prior candidate:** backend 0.6.0, last failed candidate commit `d99a52e014e2471fe14e2e65892163871f810f42`; [Backend CI #43285511530](https://github.com/KRMRGold/SMH-Tree/actions/runs/43285511530) exposed incorrect latest-event ordering when multiple UUIDv7 records shared a second-level timestamp. The repaired query uses SQLite insertion order (`rowid DESC`) for append-only status and assessment event streams.
- **Candidate verification commit:** `0f3b8bdf0a321fb20a9f41f6797812e648b73187`.
- **Run date:** 2026-11-12 UTC.
- **Automated CI:** PASS — [Backend CI #43285806228](https://github.com/KRMRGold/SMH-Tree/actions/runs/43285806228), Python 3.12, 77 passed in 4.94s.
- **Coverage added:** claim/source registration and scope; origin `derived_from` links to messages, runs, and sources; status policy and latest-per-scope projection; corroborated/default versus contested/project status; independent latest assessment per dimension; evidence/source visibility; directional contradiction relations and contradiction basis; append-only triggers; project/global access filtering including linked-record leakage prevention; open-question transitions; claim FTS; unified branch-aware search; contested-claim context with contradiction partner; M0–M5 regression suite.
- **Windows verification:** NOT RUN — user-run verification is still required.
- **Release tags:** Pending. Create failed `backend-v0.6.0` at `d99a52e014e2471fe14e2e65892163871f810f42`; create passing `backend-v0.6.1` at `0f3b8bdf0a321fb20a9f41f6797812e648b73187`.
- **Acceptance status:** CANDIDATE — CI passed; Windows verification and release tags remain outstanding.

# Test Record

## M5 accepted — context compiler and inspector

- **Candidate version:** backend 0.5.0.
- **Implementation commit:** fdf74b171d0ff838db29002df5f38ac0dbe3b7b5.
- **Latest candidate verification commit:** 31ad365f2a94bbe69bed5772dd34449c5fd758ec.
- **Run date:** 2026-11-12 UTC.
- **Automated CI:** PASS — [Backend CI #64](https://github.com/KRMRGold/SMH-Tree/actions/runs/43131791949), Python 3.12.16, pytest 9.2.0, 64 passed in 2.98s.
- **Coverage added:** deterministic packet compilation; current-message deduplication; user head-and-tail truncation with original storage preserved; system overflow; project/memory/history selection; remote memory filtering and explicit sharing settings; newest-first history and omission marker; snapshot creation and immutability; inspector authentication and retrieval; exact remote audit refs/byte count; snapshots retained after provider failure/cancellation; existing M0–M4 regression suite.
- **Windows verification:** PASS — user-reported `uv run pytest` from `backend/`, Windows (`win32`), Python 3.12.13, pytest 9.2.0, 64 passed in 9.69s.
- **Release tag:** PASS — annotated tag `backend-v0.5.0` exists on GitHub and points to `31ad365f2a94bbe69bed5772dd34449c5fd758ec`. The tag ref and annotated-tag object were independently fetched and verified.
- **Acceptance status:** ACCEPTED — implementation, CI, user-reported Windows test run, and release tag all verified.

## Latest accepted run — M4

- **Accepted version:** backend 0.4.1 (M4 — Scoped memory).
- **Implementation commit:** 0cfbbcc0d34a74264628a15f76275fe115ce787f.
- **Accepted documentation commit:** f4c6e9ad7bdee58623f60a0e5c3186b5b687d5a5.
- **Failed candidate:** backend 0.4.0, commit 41ae1363fd2ceb79fa9e117b1d237d4db526dc84; CI run #43116076972: 53 passed, 1 failed because the test created ancestor memory after the fork and expected it to be inherited.
- **Failed-candidate tag:** `backend-v0.4.0` → 41ae1363fd2ceb79fa9e117b1d237d4db526dc84.
- **Accepted tag:** `backend-v0.4.1` → f4c6e9ad7bdee58623f60a0e5c3186b5b687d5a5.
- **Tag evidence:** User confirmed tags were pushed; prior session reported their targets verified. Current connector cannot independently enumerate tag refs.
- **Run date:** 2026-11-11.
- **Automated CI:** PASS — [Backend CI #15](https://github.com/KRMRGold/SMH-Tree/actions/runs/43116317844), Python 3.12.16, pytest 9.2.0, 55 passed in 3.15s.
- **Windows verification:** PASS — user-reported Windows (`win32`), Python 3.12.13, `uv run pytest`, 55 passed in 6.87s.
- **Schema:** migration 0003 adds database-enforced memory scope and supersession invariants.
- **Coverage:** scoped CRUD, FTS5 search, branch ancestry fork-time cutoffs, sibling exclusion, remote global/user sharing, lifecycle transitions, database invariants, and API authorization.
- **Acceptance status:** ACCEPTED — automated CI passed; Windows verification and tag completion were confirmed by the user, with tag target verification reported in the preceding session.

## Latest accepted run — M3

- **Accepted version:** backend 0.3.1 (M3 — Remote gate and audit)
- **Implementation/tag commit:** c61c8a9398e3ce008c40da25a647806827e1df7a
- **Accepted tag:** `backend-v0.3.1`
- **Failed-candidate tag:** `backend-v0.3.0` → 0d106009302e235cec68850b0a1c52892eb9bc34
- **Failed first attempt:** backend 0.3.0, CI run [#13](https://github.com/KRMRGold/SMH-Tree/actions/runs/43113745788), 43 passed and 1 failed due to a stale schema-version assertion. The version was not reused.
- **Run date:** 2026-11-11
- **Automated CI:** PASS — [Backend CI #14](https://github.com/KRMRGold/SMH-Tree/actions/runs/43113953986), Python 3.12.16, 44 passed in 2.30s.
- **Windows verification:** PASS — user-reported Windows (`win32`), Python 3.12.13, `uv run pytest`, 44 passed in 6.23s.
- **Tag verification:** PASS — GitHub refs independently verified: `backend-v0.3.0` → 0d106009302e235cec68850b0a1c52892eb9bc34; `backend-v0.3.1` → c61c8a9398e3ce008c40da25a647806827e1df7a.
- **Coverage added:** denied remote calls do not invoke the provider or create an audit row; allowed remote calls have a committed audit row before provider invocation; local calls are not audited; global/user memory is stripped unless the matching setting is enabled; audit update/delete operations are rejected; authenticated audit listing is covered.
- **Acceptance status:** ACCEPTED — CI, user-run Windows verification, and both release tag targets verified.


## Previous accepted run — M2

- **Accepted version:** backend 0.2.1 (M2 — Provider layer and chat streaming)
- **Implementation commit:** ee757c186acf20d31d3fcc0b5a20292cd80ee530
- **Accepted tag:** `backend-v0.2.1`
- **Tag target:** a6dd5a9808a9ea235befbd205a45fe70baf56067 (documentation follow-up commit; tested M2 implementation unchanged)
- **Failed-candidate tag:** `backend-v0.2.0` → e1eb64313d312c530b866ddfca8eda59dc9391ce.
- **Tag verification:** Both tag refs were fetched from GitHub and their commit targets matched exactly.
- **Run date:** 2026-11-11
- **CI environment:** GitHub Actions, Ubuntu 26.04, Python 3.12.16, pytest 9.2.0.
- **Workflow run:** [Backend CI #12](https://github.com/KRMRGold/SMH-Tree/actions/runs/43111577117)
- **CI command:** `uv sync --dev`; `uv run pytest`
- **CI result:** PASS — 38 passed in 2.42s.
- **Additional local run:** User-reported Windows (`win32`), Python 3.12.13, `uv run pytest`; PASS — 38 passed in 5.71s.
- **Acceptance status:** ACCEPTED — automated suite, cross-platform local verification, and required tags verified.

## M2 acceptance checks

| Acceptance evidence | Result | Evidence |
|---|---|---|
| Failed candidate identity preserved | PASS | `backend-v0.2.0` points to e1eb64313d312c530b866ddfca8eda59dc9391ce |
| Passing candidate tag | PASS | `backend-v0.2.1` points to a6dd5a9808a9ea235befbd205a45fe70baf56067 |
| Cross-platform local test run | PASS | User-reported Windows, Python 3.12.13, 38 passed in 5.71s |

| Check | Result | Evidence |
|---|---|---|
| Existing M0/M1 regression suite | PASS | All 30 previous tests pass in the 38-test run |
| Provider protocol and registry | PASS | Provider listing and model discovery tests |
| Ollama adapter | PASS | Mock HTTP server; model listing and ordered NDJSON token stream |
| OpenAI-compatible adapter | PASS | Mock HTTP server; ordered SSE token stream |
| Token streaming order | PASS | Fake-provider SSE integration test |
| Assistant message persisted once on completion | PASS | Branch history contains exactly one completed assistant message |
| Provider error event and failed run | PASS | SSE error event; run and step status are failed |
| Cancellation marks run cancelled | PASS | Async cancellation test; no partial assistant message persisted |
| Remote provider blocked without explicit opt-in | PASS | Request rejected before provider invocation |
| Candidate version and CI result | PASS | backend 0.2.1, exact commit and CI run above |

## M2 source inspection

- Existing `runs` and `run_steps` tables from migration 0001 were reused; no migration or runtime dependency was added.
- Provider API keys are passed per request in `X-Provider-API-Key`; they are not included in run input/output records.
- Remote transmission remains opt-in at the chat request boundary. Formal policy enforcement, memory scope filtering, and transmission audit are M3.
- Provider endpoints are configured through environment variables. Persistent provider configuration via `POST /v1/providers` remains deferred.


## Previous accepted milestone — M1

- **Version:** backend 0.1.0 (M1 — Conversations and branching)
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

- Live Ollama runtime with an installed model; the adapter was tested against a local mocked HTTP server.
- Live OpenAI-compatible remote provider; the adapter was tested against a mocked HTTP server and no real API key or user data was transmitted.
- Desktop and end-to-end flows remain M8–M9 work.
