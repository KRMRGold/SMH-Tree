# Cognitive Platform: Build Specification (Desktop MVP)

**Spec version:** 0.5.0. This is a living document: update it in place and let Git history keep prior revisions.

Derived from "Distributed Cognitive Architecture v0.4". The vision document says what the system should become. This document says exactly what to build first, and in what order. Where the two disagree, this document wins for the MVP.

---

## 0. Instructions for the LLM builder

Read this section first and follow it for the whole build.

1. **Build one milestone at a time** (section 12). Do not start milestone N+1 until every acceptance test for milestone N passes.
2. **Decisions in section 2 are locked.** Do not substitute libraries. Do not add dependencies not listed without writing a one-line justification in `docs/decisions.md`.
3. **Do not build anything listed in section 13 (Non-goals).** The extension points exist so those can be added later without rewrites. They are not to be implemented now.
4. **Deterministic code owns:** permissions, validation, IDs, token budgeting, SQL, versioning, remote-transmission gating. Models are only called for generation, extraction and (later) judgment.
5. **Every milestone ends with:** passing tests, an in-place update to the single `docs/MAINTENANCE.md` (accepted version, evidence, deferred items), an updated `docs/TEST_RECORD.md`, a clean `git commit`, and a Git tag for the candidate (section 1A).
6. If a requirement is ambiguous, pick the simplest reading, record it in `docs/decisions.md`, and continue. Do not stop to ask.
7. Tests are part of the deliverable. Code without tests for its acceptance criteria is not done.
8. **This project adopts the Development State Machine Workflow.** Section 1A is the operative summary. Never claim a check passed unless you executed it against the exact commit; mark checks you cannot run as BLOCKED or NOT RUN with the reason and the minimum human action needed. Keep one current file per document and update it in place; never create versioned copies.
9. **At the start of every session,** read `docs/MAINTENANCE.md` and `docs/TEST_RECORD.md` to recover current state. If something needed is missing or inconsistent, say so and recover from Git before asking the user.

---

## 1. Product definition

A Windows-first desktop app (developed cross-platform) that gives the user **persistent, branching, memory-backed AI conversations** with an **epistemic record** of claims, evidence and contradictions, running on a **local Python backend** and **optional remote models**.

### What "done" means for the MVP

A user can:

1. Create a project and start a conversation.
2. Chat with a local (Ollama) or remote model, with streamed responses.
3. Branch a conversation at any message; each branch inherits history up to the fork and then diverges independently.
4. Have the system retain scoped memory (global / user / project / conversation / branch) that is automatically included in later prompts via a context compiler, with a visible "what was sent to the model" inspector.
5. Record claims with sources, link evidence, mark contradictions, and see epistemic status that is scoped and never silently overwritten.
6. Use the app fully offline with a local model, and never have local data sent to a remote provider unless that specific task is allowed to.

---

## 1A. Workflow adoption (Development State Machine)

This section records adoption per the workflow's own setup rules. The reusable workflow lives in the Meta-Modules repository (`workflows/Development-State-Machine-Workflow.md`) and is linked, not copied. If the builder cannot access it, say so, then follow this section as the operative summary.

| Item | Value |
|---|---|
| Adopted workflow | Development State Machine Workflow, internal `version: 1.6.0` (adoption provenance only; follow the current canonical workflow unless a pin with a Git SHA or tag is recorded here) |
| Optional modules | Testing and Verification (`0.1.1`) for the test inventory and layers; Context Continuity (`0.1.1`) for resuming across sessions |
| Initial design | this file, `BUILD_SPEC.md` (S1 and S2 are complete; S3 is satisfied per milestone) |
| Maintenance document | `docs/MAINTENANCE.md` |
| Latest test record | `docs/TEST_RECORD.md` |
| Milestone document | `docs/MILESTONE.md`, created only at S11 |
| Decisions log | `docs/decisions.md` |
| Code and tests | `backend/` and `backend/tests/`; `desktop/` and `desktop/tests/` |

**Justified adaptations**

1. **Milestones are workflow passes.** Each of M0 to M9 is one pass through S3 to S10. The acceptance tests listed under a milestone are its S3 acceptance criteria, so the builder starts at S4. Bug fixes inside a milestone use the lightweight path.
2. **Versioning (SemVer, independent sequences).** The backend package (`pyproject.toml`), the desktop app (`package.json`), the HTTP API (`/v1` in the path; a breaking change means `/v2`), and the database schema (migration number) are versioned separately. Both code artifacts stay `0.x.y` until M9 is accepted, then become `1.0.0`. A milestone candidate bumps MINOR; a repair bumps PATCH. Example: M1 produces `backend-v0.1.0`; if testing fails, the repair is `backend-v0.1.1`.
3. **Candidate, failed, accepted.** Tag every candidate in Git (`backend-v0.1.0`, `desktop-v0.8.0`). Never move or reuse a tag. A failed candidate keeps its tag and its evidence; the repair gets a new tag. Acceptance status (candidate, failed, accepted, superseded) is recorded in `docs/MAINTENANCE.md`, never implied by a version number.
4. **Living documents.** `BUILD_SPEC.md`, `docs/MAINTENANCE.md`, `docs/TEST_RECORD.md`, `docs/decisions.md` and `docs/MILESTONE.md` each exist as exactly one file, updated in place. Git history is the archive. No `-v2`, `-old` or backup copies.
5. **Verification evidence.** The builder runs every check its environment permits and records PASS, FAIL, BLOCKED or NOT RUN per check in `docs/TEST_RECORD.md`, with the exact commit, commands and results. Checks that need Windows, a real Ollama model, or a remote API key are BLOCKED or NOT RUN if unavailable, with the minimum human action stated. A critical check that is BLOCKED prevents accepting that milestone unless the user explicitly accepts the documented limitation. M9's clean-Windows-machine checks are the main expected human-run checks.
6. **Maintenance document contents.** After a milestone passes its gate, update `docs/MAINTENANCE.md` with the accepted version and commit, implemented behavior, tests run and their results, known limitations, failed candidates and outcomes, deferred work, and the adopted workflow version.
7. **Milestone document (S11).** When the user declares the MVP complete (after M9), reconcile `BUILD_SPEC.md`, `docs/MAINTENANCE.md` and the accepted code into `docs/MILESTONE.md`, then test whether a fresh LLM session can reconstruct the app from it.

---

## 2. Locked decisions

| Area | Decision |
|---|---|
| Desktop shell | Electron, Windows-first. Electron Forge for packaging (M9 only). |
| Frontend | Plain HTML/CSS/JS, native ES modules. No framework. Vite optional for dev. |
| Backend | Python 3.12, single process, FastAPI + Pydantic v2, `uv` for env management. |
| Canonical store | SQLite (WAL mode), FTS5 for search. Stdlib `sqlite3` with a thin repository layer. No ORM. |
| Migrations | Plain numbered `.sql` files plus a `schema_migrations` table. |
| IDs | UUIDv7 as text, generated in Python only. |
| Timestamps | UTC ISO-8601 text, generated in Python only. |
| Graph | **No graph database.** Relationships live in a generic `links` table (section 4.4). |
| Knowledge frameworks | Graphiti and Cognee are **not** dependencies in the MVP. They sit behind the `KnowledgeIndex` interface (section 9) for later evaluation. |
| Orchestration | LangGraph, introduced at M7 only. Chat works without it. |
| Models | `ModelProvider` adapter interface. Ollama (local) and one OpenAI-compatible HTTP provider (remote) in the MVP. |
| API | HTTP + JSON under `/v1`, SSE for streaming. WebSockets are not used. |
| Security | Loopback bind, per-launch bearer token, Electron context isolation + sandbox, no Node in renderer. |
| Tests | pytest (backend), Node built-in test runner (frontend units), Playwright (E2E, M9). |
| Token counting | Pluggable `TokenCounter`. Default is a conservative `ceil(len(text)/3.5)` estimate. Provider-specific counters can be added later. |

---

## 3. Repository layout

```
cognitive-platform/
├── README.md
├── BUILD_SPEC.md
├── docs/
│   ├── decisions.md
│   ├── MAINTENANCE.md
│   ├── TEST_RECORD.md
│   └── MILESTONE.md             # created at S11 only
├── backend/
│   ├── pyproject.toml
│   ├── src/cogplat/
│   │   ├── main.py                  # FastAPI app factory, startup, token auth
│   │   ├── config.py                # env + data-dir resolution
│   │   ├── db/
│   │   │   ├── connection.py        # sqlite open, pragmas, migration runner
│   │   │   └── migrations/0001_init.sql ...
│   │   ├── domain/                  # Pydantic models = the shared data contract
│   │   │   ├── ids.py  enums.py  conversation.py  memory.py
│   │   │   ├── epistemic.py  execution.py  context.py
│   │   ├── repos/                   # one repository per aggregate
│   │   ├── services/
│   │   │   ├── conversations.py     # branching logic
│   │   │   ├── memory.py
│   │   │   ├── epistemic.py
│   │   │   ├── permissions.py       # deterministic access checks
│   │   │   ├── context_compiler.py
│   │   │   └── remote_gate.py       # remote transmission policy + audit
│   │   ├── providers/
│   │   │   ├── base.py  ollama.py  openai_compat.py  registry.py
│   │   ├── knowledge/
│   │   │   ├── index.py             # KnowledgeIndex Protocol
│   │   │   └── sqlite_fts.py        # default implementation
│   │   ├── workflows/               # LangGraph, M7
│   │   └── api/v1/                  # routers + SSE
│   └── tests/
├── desktop/
│   ├── package.json
│   ├── main/        # Electron main: window, backend supervisor
│   ├── preload/     # restricted contextBridge API
│   └── renderer/    # HTML/CSS/JS modules
└── scripts/         # dev run, packaging helpers
```

---

## 4. Data model (SQLite)

All tables include `id TEXT PRIMARY KEY` (UUIDv7) and `created_at TEXT NOT NULL`. Enable `PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;` on every connection. Enum columns use `CHECK` constraints that mirror the Python enums.

### 4.1 Core entities

```sql
CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);

CREATE TABLE projects (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
  created_at TEXT NOT NULL, archived_at TEXT
);

CREATE TABLE conversations (
  id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id),
  title TEXT NOT NULL, root_branch_id TEXT,         -- set after first branch insert
  created_at TEXT NOT NULL, archived_at TEXT
);

CREATE TABLE branches (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id),
  parent_branch_id TEXT REFERENCES branches(id),     -- NULL for root branch
  fork_message_id TEXT REFERENCES messages(id),      -- last inherited message; NULL for root
  name TEXT NOT NULL, created_at TEXT NOT NULL,
  CHECK ((parent_branch_id IS NULL) = (fork_message_id IS NULL))
);

CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  branch_id TEXT NOT NULL REFERENCES branches(id),
  seq INTEGER NOT NULL,                              -- per-branch, starts at 1
  role TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool')),
  participant TEXT NOT NULL,                         -- 'user' | agent/model label
  content TEXT NOT NULL,
  model_ref TEXT,                                    -- provider:model for assistant msgs
  created_at TEXT NOT NULL,
  UNIQUE (branch_id, seq)
);
CREATE VIRTUAL TABLE messages_fts USING fts5(content, content='messages', content_rowid='rowid');
-- plus triggers to keep messages_fts in sync (insert/update/delete)
```

**Branch history resolution** (implement in `services/conversations.py`, test heavily):

```sql
-- Messages visible on branch :b = own messages + ancestors' messages up to each fork point.
WITH RECURSIVE chain(branch_id, upto_seq, depth) AS (
  SELECT b.id, NULL, 0 FROM branches b WHERE b.id = :b
  UNION ALL
  SELECT p.id, fm.seq, c.depth + 1
  FROM chain c
  JOIN branches cb ON cb.id = c.branch_id
  JOIN branches p  ON p.id = cb.parent_branch_id
  JOIN messages fm ON fm.id = cb.fork_message_id
)
SELECT m.* FROM chain c
JOIN messages m ON m.branch_id = c.branch_id AND (c.upto_seq IS NULL OR m.seq <= c.upto_seq)
ORDER BY c.depth DESC, m.seq ASC;
```

Rules: messages are append-only; a fork never copies messages; a sibling branch's messages are never visible; deleting is soft (`archived_at`) at the conversation level only.

### 4.2 Memory

```sql
CREATE TABLE memory_items (
  id TEXT PRIMARY KEY,
  scope TEXT NOT NULL CHECK (scope IN ('global','user','project','conversation','branch','agent')),
  scope_id TEXT,                                     -- NULL for global/user; else the owning id
  kind TEXT NOT NULL CHECK (kind IN ('preference','fact','decision','goal','procedure','open_question','pattern')),
  content TEXT NOT NULL,
  importance INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active','outdated','superseded','archived')),
  superseded_by TEXT REFERENCES memory_items(id),
  origin_kind TEXT NOT NULL CHECK (origin_kind IN ('user','agent','extraction','import')),
  origin_ref TEXT,                                   -- message id, run id, etc.
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE memory_fts USING fts5(content, content='memory_items', content_rowid='rowid');
```

Memory in an ancestor scope is eligible for a narrower context only per section 8. A memory is never globally visible just because it exists.

### 4.3 Epistemic records

Claims, evidence, arguments and evaluations are separate objects. History is append-only. Nothing is "resolved" by overwriting.

```sql
CREATE TABLE sources (
  id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id),
  kind TEXT NOT NULL CHECK (kind IN ('document','url','message','user_statement','agent_output','dataset')),
  title TEXT, uri TEXT,                              -- uri may be a file path under data/sources/
  content_hash TEXT,                                 -- sha256 of canonical content
  retrieved_at TEXT, created_at TEXT NOT NULL
);

CREATE TABLE claims (
  id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id),
  claim_type TEXT NOT NULL CHECK (claim_type IN ('factual','causal','normative','predictive','definition','other')),
  text TEXT NOT NULL,                                -- natural-language statement (always required)
  subject TEXT, predicate TEXT, object TEXT,         -- optional structured triple
  valid_from TEXT, valid_to TEXT,                    -- temporal validity (nullable)
  origin_kind TEXT NOT NULL CHECK (origin_kind IN ('user','agent','extraction','import')),
  origin_ref TEXT, observed_at TEXT, created_at TEXT NOT NULL
);

-- Status is an event log, not a column. Current status = latest event per (claim_id, scope).
CREATE TABLE claim_status_events (
  id TEXT PRIMARY KEY, claim_id TEXT NOT NULL REFERENCES claims(id),
  status TEXT NOT NULL CHECK (status IN
    ('proposed','reported','inferred','corroborated','contested','accepted','rejected','superseded','unresolved','unknown')),
  scope TEXT NOT NULL DEFAULT 'default',             -- e.g. 'project:<id>', 'default'
  policy TEXT,                                       -- evaluation policy name, REQUIRED when status='accepted'
  rationale TEXT, actor_kind TEXT NOT NULL CHECK (actor_kind IN ('user','agent','system')),
  actor_ref TEXT, created_at TEXT NOT NULL,
  CHECK (status <> 'accepted' OR policy IS NOT NULL)
);

-- Separate dimensions, never one universal confidence score.
CREATE TABLE claim_assessments (
  id TEXT PRIMARY KEY, claim_id TEXT NOT NULL REFERENCES claims(id),
  dimension TEXT NOT NULL CHECK (dimension IN
    ('source_reliability','evidence_strength','extraction_reliability','verification_status','temporal_validity','argument_strength')),
  value_num REAL CHECK (value_num BETWEEN 0 AND 1), value_text TEXT,
  rationale TEXT, actor_kind TEXT NOT NULL, actor_ref TEXT, created_at TEXT NOT NULL
);

CREATE TABLE evidence (
  id TEXT PRIMARY KEY, claim_id TEXT NOT NULL REFERENCES claims(id),
  source_id TEXT NOT NULL REFERENCES sources(id),
  stance TEXT NOT NULL CHECK (stance IN ('supports','challenges','context')),
  excerpt TEXT, locator TEXT,                        -- page/line/timestamp within the source
  created_at TEXT NOT NULL
);

CREATE TABLE claim_relations (
  id TEXT PRIMARY KEY,
  from_claim_id TEXT NOT NULL REFERENCES claims(id),
  to_claim_id   TEXT NOT NULL REFERENCES claims(id),
  rel TEXT NOT NULL CHECK (rel IN ('contradicts','supports','supersedes','refines','depends_on')),
  contradiction_basis TEXT CHECK (contradiction_basis IN ('direct','different_time','different_context','different_definition','unclear')),
  note TEXT, created_at TEXT NOT NULL
);

CREATE TABLE open_questions (
  id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id),
  text TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open','investigating','answered','dropped')),
  related_claim_id TEXT REFERENCES claims(id), created_at TEXT NOT NULL
);
```

Arguments (premises/inferences/counterarguments) are **deferred** past the MVP. Reserve `claim_relations.rel IN ('supports','depends_on')` for now. Do not add argument tables yet.

### 4.4 Generic links (the logical graph layer)

One table connects any object to any other, which is how conversation, knowledge, memory and execution "graphs" reference each other without being flattened. It migrates cleanly to a real graph backend later.

```sql
CREATE TABLE links (
  id TEXT PRIMARY KEY,
  from_type TEXT NOT NULL, from_id TEXT NOT NULL,    -- 'message','claim','memory_item','source','run','task',...
  to_type   TEXT NOT NULL, to_id   TEXT NOT NULL,
  rel TEXT NOT NULL,                                 -- 'introduces','derived_from','references','answers','produced_by',...
  created_by_kind TEXT NOT NULL, created_by_ref TEXT, created_at TEXT NOT NULL,
  UNIQUE (from_type, from_id, to_type, to_id, rel)
);
CREATE INDEX links_from ON links(from_type, from_id);
CREATE INDEX links_to   ON links(to_type, to_id);
```

Provenance uses `rel='derived_from'` (derived item to original source/message/run). Original material is canonical. Summaries and extractions are derived and must carry a `derived_from` link.

### 4.5 Execution, settings, audit

```sql
CREATE TABLE runs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL,           -- 'chat_turn','extract_claims','curate_memory'
  conversation_id TEXT, branch_id TEXT,
  status TEXT NOT NULL CHECK (status IN ('pending','running','succeeded','failed','cancelled')),
  allow_remote INTEGER NOT NULL DEFAULT 0, input_json TEXT, output_json TEXT, error TEXT,
  started_at TEXT, finished_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE run_steps (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), seq INTEGER NOT NULL,
  name TEXT NOT NULL, status TEXT NOT NULL, detail_json TEXT, created_at TEXT NOT NULL
);
CREATE TABLE provider_configs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('ollama','openai_compat')),
  label TEXT NOT NULL, base_url TEXT NOT NULL, is_remote INTEGER NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1                 -- API keys are NOT stored here (section 11.3)
);
CREATE TABLE context_snapshots (                     -- powers the "what was sent" inspector
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
  provider_label TEXT NOT NULL, packet_json TEXT NOT NULL, token_estimate INTEGER NOT NULL, created_at TEXT NOT NULL
);
-- M5 migration 0004 adds a unique index on context_snapshots(run_id) and
-- BEFORE UPDATE / BEFORE DELETE triggers. Snapshots are immutable, one per
-- successfully compiled chat_turn. Do not rewrite migration 0001.
CREATE TABLE remote_transmissions (                  -- append-only audit of anything sent off-device
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
  provider_label TEXT NOT NULL, item_refs_json TEXT NOT NULL, byte_count INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE settings (key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL);
```

---

## 5. Shared data contract (Pydantic)

All API request/response bodies and all service boundaries use Pydantic models in `domain/`. Each public model carries `schema_version: int = 1`. Example of the contract's shape (implement all entities in section 4 in the same style):

```python
class EpistemicStatus(StrEnum):
    proposed="proposed"; reported="reported"; inferred="inferred"; corroborated="corroborated"
    contested="contested"; accepted="accepted"; rejected="rejected"; superseded="superseded"
    unresolved="unresolved"; unknown="unknown"

class Claim(BaseModel):
    schema_version: int = 1
    id: str
    project_id: str | None
    claim_type: ClaimType
    text: str
    subject: str | None = None; predicate: str | None = None; object: str | None = None
    valid_from: datetime | None = None; valid_to: datetime | None = None
    origin: Origin                       # kind + ref
    current_status: list[ScopedStatus]   # latest event per scope
    assessments: list[Assessment]        # latest per dimension
    evidence: list[EvidenceRef]
    relations: list[ClaimRelation]
```

Rules:
- Validate on the way in **and** out. Unknown enum values fail loudly.
- Status is derived from the event log. Never write a "current status" field.
- `accepted` requires a `policy` (also enforced by the SQL CHECK).
- Never collapse the assessment dimensions into a single score anywhere in code or UI.

---

## 6. Permissions (deterministic)

`services/permissions.py` exposes one function used by everything that reads memory, claims or messages for a model:

```python
@dataclass(frozen=True)
class AccessContext:
    user_id: str; project_id: str | None; conversation_id: str | None
    branch_id: str | None; agent_id: str | None; allow_remote: bool

def visible_memory_scopes(ctx: AccessContext) -> list[tuple[str, str | None]]: ...
def can_read(ctx: AccessContext, obj_type: str, obj_id: str) -> bool: ...
```

Scope eligibility for memory, given a request on branch B of conversation C in project P:

| Memory scope | Eligible when |
|---|---|
| `global`, `user` | always (local use). For **remote** tasks, only if `settings.share_<scope>_memory_remote = true`. |
| `project` | `scope_id == P` |
| `conversation` | `scope_id == C` |
| `branch` | `scope_id` is B **or an ancestor of B** (inherited up to the fork point; items created after the fork on the ancestor are excluded by `created_at <= fork message created_at`) |
| `agent` | `scope_id == ctx.agent_id` |

Sibling-branch memory is never eligible. Test this explicitly.

---

## 7. Provider layer and remote gate

```python
class ChatMessage(BaseModel): role: str; content: str
class ModelProvider(Protocol):
    label: str; is_remote: bool
    async def list_models(self) -> list[str]: ...
    async def stream_chat(self, model: str, messages: list[ChatMessage], **opts) -> AsyncIterator[str]: ...
    async def embed(self, model: str, texts: list[str]) -> list[list[float]]: ...   # optional per provider
```

**Remote gate** (`services/remote_gate.py`), enforced in code and not via prompts:

1. Every run has `allow_remote` (default **false**).
2. `assert_may_send(run, provider, packet)`: if `provider.is_remote` and not `run.allow_remote` then raise `RemoteNotAllowed`.
3. Items in the packet from `global`/`user` memory scopes are stripped for remote providers unless the matching setting is on.
4. On every allowed remote send, write one `remote_transmissions` row listing the item refs and byte count, **before** the HTTP call.
5. API keys are never stored in SQLite or the repo. See 11.3.

---

## 8. Context compiler and inspector (M5)

The context compiler is pure, deterministic, and unit-testable. It makes no model calls. It is the **single authority** for deciding which eligible information enters a model request. Sources provide candidates; they do not inject content directly into provider requests.

### 8.1 Contract

```python
def compile_context(
    connection: sqlite3.Connection,
    req: CompileRequest,
    counter: TokenCounter | None = None,
) -> ContextPacket: ...
```

`CompileRequest` contains:
- A validated `AccessContext`, including conversation, project, branch ancestry, remote permission and fork-time cutoffs.
- The current user message and its canonical message ID.
- Provider label and model identifier.
- Configured maximum input tokens and reserved output tokens.
- The compiler/configuration version needed to reproduce the selection policy.

The provider/model context profile supplies the input limit and output reserve. Do not guess a model's capacity from its name. If no model-specific profile exists, use the configured conservative application default. Reject invalid limits and any configuration where the output reserve leaves no usable input budget. Until model-specific profiles are introduced, M5 uses `COGPLAT_DEFAULT_MAX_INPUT_TOKENS` (default `8192`) and `COGPLAT_DEFAULT_RESERVE_OUTPUT_TOKENS` (default `1024`).

The M5 default token counter estimates `ceil(len(text) / 3.5)` tokens per message body plus four tokens of role/framing overhead per message. The fixed mandatory system instructions are defined by the context compiler; they are counted like any other message and are never truncated.

The normalized `ContextPacket` contains:
- Ordered provider-neutral messages.
- Included source references, with source type and scope.
- Excluded candidate references and deterministic exclusion reasons.
- Token estimates, input limit, output reserve, and section allocations.
- Transformations, including truncation markers and omitted character/token estimates.
- Provider/model labels and compiler version.

Provider adapters render the normalized packet into their wire format. API keys and other credentials must never appear in the packet, snapshot, run record, or logs.

### 8.2 Candidate sources in M5

M5 implements these sources only:

1. **System instructions:** fixed application instructions. These are mandatory and are never truncated or silently omitted.
2. **Project context:** project description, when present. Optional and subject to the context budget.
3. **Memory:** active items visible through the existing M4 scope rules. Candidate selection uses FTS5 matches against the current user message, plus high-importance items (`importance >= 4`) and preference items. Deduplicate by canonical memory ID.
4. **Conversation history:** resolved branch history using the existing M1 resolver. The current user message is supplied separately and must not be duplicated from the persisted history.

M5 does not include claims or other epistemic records; those arrive in M6 through a future context-source extension. M5 does not add model-based relevance ranking, embeddings, vector search, or background memory curation.

All memory visibility, including branch ancestry cutoffs and remote global/user sharing settings, must reuse M4's permission logic. Do not create a parallel permission implementation.

### 8.3 Deterministic selection and budget policy

Let `input_budget = max_input_tokens - reserve_output_tokens`. Token estimates use the configured `TokenCounter`; the default remains the conservative `ceil(len(text)/3.5)` estimate. Count the rendered packet, including role/message overhead as represented by the counter, not only raw source text.

Selection policy:

1. Validate limits and build the mandatory system instructions and current user message.
2. If system instructions alone exceed the input budget, fail compilation with a typed, inspectable error. Never truncate system instructions.
3. If system instructions plus the current user message exceed the budget, deterministically truncate the **current user message** using head-and-tail preservation. Keep the beginning and end, insert an explicit marker such as `[... N characters omitted ...]`, and record the exact transformation. Preserve the original message unchanged in conversation storage.
4. With the remaining budget, include optional project context, then eligible memory up to a maximum of 25% of the usable input budget, then history using the remaining capacity. Unused memory allocation may flow to history; the memory cap may not be exceeded.
5. Select history newest-first so recent context wins. If older history is omitted, include one marker with the count of omitted messages. Render selected history in chronological order.
6. Order memory candidates deterministically: FTS relevance first, then importance descending, creation time descending, and canonical ID ascending as the final tie-breaker. Include only whole memory items; do not silently cut an individual memory record.
7. If the final normalized packet still exceeds the budget due to rendering overhead, remove the lowest-priority optional item and recalculate. Repeat deterministically. If no optional content remains and the mandatory system plus truncated user message still cannot fit, fail clearly without calling the provider.

The current user message is therefore preserved as much as possible and is truncated only after optional content has been excluded. System instructions are never truncated. No content is silently dropped: every omission is represented in packet metadata, and user-message truncation is represented in the rendered text.

### 8.4 Remote authorization and final packet

Remote filtering is part of compilation's finalization path, not a later provider-side content mutation:

1. Compile only from sources eligible under the validated access context.
2. For remote providers, exclude global/user memory unless the corresponding M4 remote-sharing setting explicitly allows it.
3. Produce the final provider-ready packet and its exact source references.
4. Apply the existing M3 remote gate to that final packet. If remote transmission is not explicitly allowed, fail closed and do not invoke the provider.
5. Persist the context snapshot and remote transmission audit before provider network I/O. The transmission audit lists only references actually present in the transmitted packet and records the byte count of the exact compact role/content packet, preserving M3's existing definition.
6. Pass the exact snapshotted packet to the provider. Do not modify it after snapshot/audit creation.

The snapshot is local inspection data; the remote audit is the record of off-device transmission. Neither may contain API keys. A local run does not create a remote-transmission record.

### 8.5 Snapshot lifecycle and inspector

Migration 0001 already defines `context_snapshots`. M5 adds migration 0004 rather than editing an applied migration:
- A unique index on `context_snapshots.run_id` enforces at most one snapshot per run.
- Database triggers reject snapshot updates and deletes.
- A snapshot is created for every **successfully compiled chat_turn**, before provider invocation. Provider failures and cancellations after compilation retain the snapshot. A run that fails before compilation completes has no packet snapshot; its run/step error records the failure.
- Non-chat runs do not require context snapshots.
- The snapshot stores the exact normalized/provider-ready messages, provider and model identifiers, token estimate, budget and source/selection/transformation metadata, and compiler version. The API key is excluded.

The authenticated inspector endpoint is `GET /v1/runs/{id}/context`. It returns the immutable snapshot for that run, or a clear not-found response if no snapshot exists. It must not reconstruct a packet from current memory or settings: the purpose is to inspect what that run actually received. The endpoint exposes only the stored, final authorized packet and its metadata.

### 8.6 Logical implementation boundaries

Keep responsibilities separable without requiring one file per responsibility:

- Candidate retrieval: memory, project and resolved history.
- Selection: deterministic ordering, deduplication and exclusion reasons.
- Budgeting: token accounting, allocation and user-message truncation.
- Rendering: normalized provider-neutral messages.
- Snapshot persistence: immutable one-per-chat-run record.
- Inspection: retrieval of the stored snapshot.

The compiler is a deterministic service. Do not introduce LangGraph or agent orchestration here; LangGraph remains M7.

### 8.7 M5 verification

Tests must cover:
- Identical inputs and configuration produce identical packet content and selection metadata.
- Current user message is not duplicated when it is already persisted in branch history.
- System instructions are never truncated; system-only overflow fails before provider invocation.
- Oversized user messages retain their head and tail, include an explicit omission marker, and leave the stored original unchanged.
- Optional project context, memory and history are omitted in deterministic priority order when budgets are tight.
- Memory selection obeys active-state, scope, branch ancestry/fork cutoffs, sibling isolation and remote-sharing settings.
- Memory ordering and tie-breaking are deterministic; no memory item is partially cut.
- History selection is newest-first, output is chronological, and omitted-history count is accurate.
- Final rendered packet never exceeds the configured input budget; output reserve is respected.
- Remote-denied requests never invoke the provider; remote packets exclude disallowed global/user memory.
- Remote audit refs and byte count describe the exact final packet and are persisted before provider invocation.
- Exactly one immutable snapshot exists for each successfully compiled chat run, including provider failure/cancellation after compilation; duplicate snapshots and update/delete attempts are rejected.
- Inspector returns the stored packet, source refs, exclusions, budget and transformations, without recompiling.
- Existing M0–M4 regression tests continue to pass.
 
## 9. Knowledge extension point

```python
class KnowledgeIndex(Protocol):
    def index(self, obj_type: str, obj_id: str, text: str, meta: dict) -> None: ...
    def search(self, query: str, ctx: AccessContext, limit: int = 20) -> list[SearchHit]: ...
    def remove(self, obj_type: str, obj_id: str) -> None: ...
```

MVP implementation: `SqliteFtsIndex` over `messages_fts`, `memory_fts` and a `claims_fts` table. Graphiti or Cognee, if adopted later, are alternative implementations that must (a) accept canonical IDs from this system, (b) write only to their own store, and (c) be read through this interface. SQLite remains canonical. No bidirectional sync.

---

## 10. API (versioned, `/v1`)

Auth: every request needs `Authorization: Bearer <launch-token>`. Missing or invalid gives 401. Bind `127.0.0.1` only. Port is chosen by Electron (free port) and passed to the backend.

| Method + path | Purpose |
|---|---|
| `GET /v1/health` | status, version, schema version, capabilities |
| `GET/POST /v1/projects` | list / create |
| `GET/POST /v1/conversations` | list / create (creates root branch) |
| `GET /v1/conversations/{id}/branches` | branch tree |
| `POST /v1/branches` | fork: `{parent_branch_id, fork_message_id, name}` |
| `GET /v1/branches/{id}/messages` | resolved history (inheritance applied) |
| `POST /v1/branches/{id}/chat` | body `{content, provider, model, allow_remote}`. Returns **SSE** (`event: token`, `event: done` with run id, `event: error`) |
| `GET /v1/runs/{id}` · `GET /v1/runs/{id}/context` | run record · context snapshot (inspector) |
| `GET/POST/PATCH /v1/memory` | scoped CRUD; `PATCH` can mark `outdated`/`superseded` |
| `GET/POST /v1/claims` · `POST /v1/claims/{id}/status` | create · append a status event |
| `POST /v1/claims/{id}/evidence` · `POST /v1/claims/{id}/relations` | attach evidence · relate or mark contradiction |
| `GET/POST /v1/sources` | register sources |
| `GET/POST /v1/open-questions` | track unresolved items |
| `GET /v1/search?q=&scope=` | FTS across messages, memory and claims, permission-filtered |
| `GET/POST /v1/providers` · `GET /v1/providers/{id}/models` | configure and discover |
| `GET /v1/transmissions` | remote audit log |

Errors use one shape: `{ "error": { "code": "...", "message": "...", "details": {} } }`. Publish OpenAPI at `/v1/openapi.json`.

---

## 11. Desktop application

### 11.1 Electron
- `contextIsolation: true`, `sandbox: true`, `nodeIntegration: false`, `webSecurity` on, a strict CSP, and navigation and `window.open` denied except to an allowlist.
- **Main process** spawns the backend, picks a free loopback port, generates a 32-byte random token, passes both via environment variables, polls `/v1/health` until ready (timeout 20 s), restarts once on crash, and kills the child on quit (including on Windows via process-tree termination).
- **Preload** exposes a minimal `window.cog` API: `getApiBase()`, `request(path, opts)` (injects the token in main so the renderer never sees it), `stream(path, opts, onEvent)` (SSE), `openExternal(url)` (allowlisted). Nothing else.

### 11.2 Renderer (vanilla JS, ES modules)
Screens, kept simple:
1. **Sidebar**: projects, conversations, branch tree.
2. **Chat**: message list, composer, streaming output, per-message "branch from here", a provider/model picker, and an explicit **"allow remote for this message"** toggle (off by default).
3. **Context inspector**: shows the last run's packet (what was sent and what was dropped).
4. **Memory panel**: list, filter by scope, add, edit, mark outdated.
5. **Claims panel**: search and inspect claims, scoped status, evidence, assessments, and relationships; compare contradictions side by side; append status updates; and create/update open questions. M8 does not include desktop authoring controls for claims, sources, evidence, assessments, or claim relationships.
6. **Settings**: providers, remote-sharing toggles for global/user memory, data location.

No UI framework. Small modules with a tiny event bus. Escape all model and user text (`textContent`, never `innerHTML` for untrusted content).

### 11.3 Secrets
Remote API keys are stored with Electron `safeStorage` (encrypted by the OS) in the user data directory, and passed to the backend per request in a header that is never logged. They never enter SQLite, logs or context snapshots.

### 11.4 Data locations (Windows)
`%APPDATA%/CognitivePlatform/` containing `app.db`, `sources/` (large documents, named by content hash), and `logs/`. Models are managed by Ollama and are never bundled.

---

## 12. Milestones and acceptance tests

Each milestone lists what to build and the tests that must pass.

**M0: Skeleton.** Repo layout, `uv` project, FastAPI app with `/v1/health` and bearer auth, config and data-dir resolution, migration runner with `0001_init.sql` (all of section 4), pytest and CI script.
- Tests: health returns 200 with a token and 401 without; migrations apply once and are idempotent; all tables exist; foreign keys are enforced.

**M1: Conversations and branching.** Repos and services for projects, conversations, branches and messages. FTS triggers. The recursive history resolver.
- Tests: linear history is correct; a fork inherits only up to the fork message; a message added to the parent after the fork is **not** visible in the child; a sibling is never visible; a fork of a fork resolves in order; `seq` uniqueness is enforced; deep chains (50 levels) resolve correctly.

**M2: Provider layer and chat streaming.** `ModelProvider`, Ollama and OpenAI-compatible adapters, `/chat` SSE endpoint, runs and run_steps. Use a fake provider in tests.
- Tests: tokens stream in order; the assistant message is persisted once on completion; a provider error produces `event: error` and a `failed` run; cancellation marks the run `cancelled`; the Ollama adapter is tested against a mocked HTTP server.

**M3: Remote gate and audit.** `permissions.py`, `remote_gate.py`, the transmissions log.
- Tests: a remote provider with `allow_remote=false` raises and nothing is sent; with `true`, the transmission row is written **before** the call; global/user memory is stripped for remote unless enabled; local providers are never logged as remote.

**M4: Memory.** CRUD, scopes, FTS, supersede/outdate flow, scope eligibility rules.
- Tests: the full eligibility table in section 6, including branch ancestry with the fork-time cutoff, and sibling exclusion; outdated and superseded items are not selected.

**M5: Context compiler and inspector.** Implement the deterministic compiler in section 8, using M4 permission and memory services and the existing branch-history resolver. Wire it into the chat run before provider invocation. Add migration 0004 to enforce one immutable context snapshot per successfully compiled chat run. Add the authenticated inspector endpoint.
- Tests: all verification cases in section 8.7; a snapshot exists for every successfully compiled `chat_turn`, including provider failure/cancellation after compilation. Runs that fail before compilation and non-chat runs do not require snapshots.
- Explicitly deferred: epistemic sources (M6), model-based ranking, embeddings, background formalization/curation, agents and LangGraph (M7).

**M6: Epistemic layer.** Sources, claims, status events, assessments, evidence, relations, open questions, and API. The compiler includes claims with status.
- Tests: `accepted` without a policy is rejected; status is derived from the latest event per scope; a claim can be `corroborated` in one scope and `contested` in another; contradicting a claim never alters the other claim's record; assessments keep dimensions separate; `contradiction_basis` is stored; a contested claim renders with its status in the compiled context, and its contradicting partner is included alongside.

**M7: Minimal LangGraph workflows and explicit claim extraction.** Introduce LangGraph as a bounded orchestration layer, not a new agent architecture. Build exactly two workflows:

1. **`chat_turn`** wraps the existing chat lifecycle in checkpointed nodes: prepare/persist the user message and run; compile and snapshot context using the existing M5/M6 services; apply the existing remote gate and audit immediately before provider I/O; stream the provider response; persist the completed assistant message and finish the run. Preserve the existing SSE event contract and completed-only assistant persistence. Keep the existing non-LangGraph path available.
2. **`extract_claims`** is explicitly invoked for one existing message through an authenticated endpoint (proposed route: `POST /v1/messages/{message_id}/extract-claims`). Load the canonical message and its project scope; use the selected provider to propose distinct claims; validate structured output and require each evidence excerpt to be an exact substring of the source message; then persist each valid claim as `proposed` with `origin_kind='extraction'`, a source/evidence record using stance `context`, a `derived_from` link to the message, and a `produced_by` link to the extraction run. Extraction never assesses truth, assigns confidence, or auto-accepts claims. No background extraction is added.

**Checkpointing and persistence.** Use LangGraph `StateGraph` and the official SQLite checkpointer in the existing `app.db`. The LangGraph `thread_id` is the existing run ID. Checkpoints are execution state, not canonical product data; existing SQLite repositories and tables remain authoritative. Use the async SQLite saver for the async FastAPI/provider path, with its required `aiosqlite` dependency. Enable strict msgpack deserialization safety / an explicit safe-module allowlist. The saver owns its checkpoint tables; do not create a second custom checkpoint schema.

**Failure and retry invariants.** A failed node resumes from the last successful checkpoint without repeating completed nodes. Extraction persistence must be idempotent across the boundary where canonical DB writes succeed but checkpoint persistence fails: persist claims, evidence, links, and the run's serialized output atomically; on retry, reuse that output rather than creating duplicates. Remote audit must likewise be idempotent per run and must match the original authorized request. Never replay a provider request merely because a later persistence step failed unless the workflow state proves it has not already completed.

**Compatibility and controls.** Add `COGPLAT_WORKFLOWS_ENABLED` (default true for M7 candidate) to select the LangGraph path. When false, existing chat behavior remains available and extraction returns a clear disabled response. Keep provider-independent Pydantic validation for extraction JSON; provider-specific structured-output APIs are not required. Remote model use remains opt-in through the existing per-run gate and audit. Add migration 0006 to store a SHA-256 digest on each remote-transmission audit row and enforce one audit row per run. Keep canonical product records in `app.db`; place LangGraph's package-owned checkpoint tables in a separate `checkpoints.db` file under the same data directory so checkpoint writes do not contend with the application's synchronous transaction path.

- Tests: enabled/disabled chat result and SSE equivalence; context snapshot and remote audit invariants; successful-node resume after a later node fails; checkpoint survival across backend restart; exact extraction evidence validation; proposed status and provenance links; malformed output writes no claims; extraction retry creates no duplicates; remote extraction is blocked without opt-in; project-scope isolation; disabled-workflow fallback; full M0–M6 regression suite. CI and user-run Windows verification are required before acceptance.

**M8: Desktop shell.** Electron main, preload and renderer screens from section 11, with backend supervision.
- Tests (Node runner + manual script): the backend starts, the port is loopback-only, calls without the token fail, the renderer cannot reach `require`/`process`, quitting leaves no orphan Python process, and a chat round trip with a fake provider works end to end.

**M9: Packaging and E2E.** PyInstaller sidecar, Electron Forge Windows installer, Playwright smoke tests. First check that the sidecar runs on a clean Windows machine **without Python installed**.
- Tests: the installer builds; the installed app launches offline; chat works with a local Ollama model; user data lives in `%APPDATA%`, not the install directory.

---

## 13. Non-goals (do NOT build in the MVP)

- Full desktop epistemic authoring: manually creating claims or sources, attaching evidence, adding assessments, and creating claim relationships. The backend contracts remain available; the desktop authoring workflows are deferred to the post-MVP extension below.
- Graphiti, Cognee, Neo4j or any graph database (extension point: `KnowledgeIndex`, section 9).
- The multi-agent "cognitive network" (Memory Curator, Research, Verification, Argumentation agents). The data model supports them; the agents come after M9.
- Argument graphs and automated evaluation of arguments.
- Autonomous background memory curation (MVP memory is user-driven plus explicit extraction).
- Cloud sync, accounts, multi-user, or any network exposure of the API.
- Integrations with Chatapp, C-2 Branching Messenger or Meta-Modules (they will consume the same `/v1` API later).
- Embeddings and vector search (FTS5 only in the MVP; the provider interface already has `embed` for later).
- Auto-update, telemetry, code signing.

---

### Post-MVP extension: epistemic authoring UI

This capability is intentionally outside M0–M9. It must not delay or alter the current M8/M9 acceptance gates. The M8 Claims panel remains an inspection and limited-management surface, not a complete epistemic editor.

**Goal:** let users deliberately create and maintain the epistemic records that the backend already supports, without weakening provenance or append-only history.

**Planned desktop workflows:**

1. **Create claims manually.** Provide a form for claim text and claim type, with optional structured subject/predicate/object and validity dates. Use the selected project scope (or global scope when no project is selected). User-originated claims use the existing backend default origin and initial `reported` status. Do not silently create claims from ordinary chat.
2. **Explicit message extraction.** Expose the existing M7 extraction endpoint as a deliberate action on one selected message. Show the provider/model choice and preserve the existing per-request remote opt-in. Extracted claims remain `proposed`, cite exact source-message excerpts, and retain their source/evidence and provenance links. No background extraction.
3. **Register sources and attach evidence.** Allow source metadata to be registered, then attach it to a claim with stance (`supports`, `challenges`, or `context`), optional exact excerpt, and locator. Do not imply that registering a URL fetches or verifies its contents; source retrieval/import is a separate capability.
4. **Add assessments.** Allow independent assessment dimensions with either a numeric value in the backend's 0–1 range or a text value, plus rationale. Never collapse dimensions into one universal confidence score.
5. **Create claim relationships.** Allow users to select another visible claim and create supported relation types. A `contradicts` relation requires an explicit contradiction basis. Display both claims without mutating either claim's content or status.
6. **Review and correct history.** Claims, sources, evidence, assessments, and relations remain append-only. Do not offer edit/delete controls that imply rewriting history. Corrections are represented by additional records or status events, with provenance retained.

**Acceptance criteria for this future feature:**

- Manual claim creation persists in the selected project/global scope with the expected initial status and origin.
- Source registration and evidence attachment preserve source IDs, stance, excerpt, locator, and scope validation.
- Assessment dimensions remain independent and append-only; invalid empty values and out-of-range numeric values are rejected.
- Relationship creation enforces valid target visibility and requires a contradiction basis only for contradictions.
- Message extraction is explicitly user-triggered, preserves exact-evidence validation and provenance, and cannot bypass remote opt-in.
- All created records remain visible after app restart and are correctly reflected in claim detail and search.
- Existing M6/M7 API and persistence invariants continue to pass.

### Post-MVP extension: local model lifecycle and routing

This capability is intentionally outside M0–M9. It must not delay or alter the current M8/M9 acceptance gates.

**Goal:** make local models easy to discover, load, unload, and select, then allow SMH-Tree to route individual tasks to suitable models without coupling conversations to one provider or model.

**Separate responsibilities:**

1. **Model Manager** — provider-specific lifecycle and availability operations. For Ollama, discover installed models and currently loaded models, request a model to load, request it to unload, and report runtime availability/resource metadata where the runtime exposes it.
2. **Model Router** — choose a provider/model for a request based on task requirements, model capability profiles, user preferences, remote permissions, current availability, and resource constraints. The router does not generate the user-facing answer.

**Implementation progression:**

- **Manual management first:** show whether the Ollama service is reachable, list installed and loaded models, and provide explicit load/unload actions. Detect and connect to an existing Ollama service; do not take ownership of starting, stopping, installing, or updating the Ollama server in the first iteration. Do not automatically download models.
- **Model profiles:** maintain editable profiles for task capabilities (general conversation, coding, reasoning, long-context, vision, tool calling, embeddings), context limits, operational constraints, and user preference. Do not infer capabilities or context capacity solely from model names.
- **Deterministic routing:** begin with transparent rules. Consider task category, required modalities/tools, configured model profiles, whether a model is installed and available, remote permission, and local resource constraints. Keep a configured default/fallback model.
- **User control:** support automatic selection, a one-message override, and a conversation-level pinned model. Show the selected provider/model and a concise reason for each automatic choice.
- **Intelligent routing later:** optionally use a lightweight classifier to categorize ambiguous tasks and recommend a model. The classifier is advisory input to deterministic policy, not the authority for permissions, resource limits, or remote transmission. Prefer a local classifier when available.
- **Lifecycle policy later:** add configurable keep-warm and idle-unload behavior only after measuring actual memory pressure and concurrent-request behavior. Do not load every installed model by default.

**Safety and correctness invariants:**

- The existing remote gate remains authoritative. Routing must never turn a local request into a remote transmission unless that specific request explicitly permits remote processing; existing memory filtering and transmission auditing remain in force.
- A requested or automatically selected model must be validated against the provider's current model inventory before dispatch.
- If no eligible model is available, use the configured eligible fallback or explain the blocker; never silently choose an unauthorized remote model.
- A model switch applies to the new request only. It must not rewrite prior messages, context snapshots, or run provenance.
- Persist the actual provider/model used and the selection mode/reason with each run so the result remains inspectable and reproducible.
- Keep provider-specific lifecycle operations behind adapters. The conversation and workflow layers should depend on stable model-management and routing contracts, not Ollama-specific API details.
- Do not introduce a multi-agent framework solely for model routing.

**Initial acceptance criteria for this future feature:**

- Ollama service availability is reported without the desktop app spawning a second Ollama server.
- Installed and currently loaded models are distinguishable.
- User can load and unload an installed model and see success/failure state.
- Profiles and default-model settings persist across app restarts.
- Manual override and conversation pinning work and are visible.
- Deterministic routing chooses only eligible models and records its explanation.
- Missing/unavailable models produce a clear fallback or actionable error.
- Remote routing is blocked by default and cannot bypass the existing remote gate.
- Tests cover inventory changes, load/unload failures, selection precedence, fallback, concurrent requests, and remote-permission invariants.

## 14. Resolved open questions (from v0.4 section 15)

| Question | MVP answer |
|---|---|
| Which graph DB? | None. SQLite plus the `links` table; revisit only if a concrete query is too slow or awkward. |
| Cognee vs Graphiti overlap? | Neither adopted. Evaluate behind `KnowledgeIndex` after M9; must not duplicate ownership. |
| Shared storage? | One SQLite file owned by the backend. External frameworks keep their own stores. |
| Sync model? | One-way: SQLite (canonical) to external index, via `KnowledgeIndex.index()`. No bidirectional sync. |
| Canonical contract? | Section 5 plus section 4 schemas, versioned by `schema_version` and migration numbers. |
| Permission propagation? | Section 6: deterministic scope table, branch ancestry with a fork-time cutoff. |
| Offline? | Local-first. Remote features are simply unavailable when offline, never required. |
| Agent results to persistent knowledge? | Always enter as `proposed` with provenance. Only a user action (or a future explicit policy) can `accept`. |
| Showing conflicts to users? | Claims panel shows contradicting claims side by side with `contradiction_basis`. |
| Local vs external? | Per-run `allow_remote` flag, default off, enforced by the remote gate and audited. |
| Versions and migrations? | Numbered SQL migrations; the API is under `/v1`; breaking changes go to `/v2`. |

---

## 15. Definition of done for the whole MVP

- All M0 to M9 acceptance tests pass.
- `README.md` documents setup (`uv sync`, `npm install`, run commands) and how to run all tests.
- A new developer can clone, run the backend tests with no network, and start the desktop app in dev mode following only the README.
- `docs/MAINTENANCE.md` lists the accepted versions, what was built, what was deferred, and any decision made that deviated from this spec; `docs/TEST_RECORD.md` holds the latest PASS, FAIL, BLOCKED and NOT RUN results.
- Every milestone candidate has a Git tag, and its acceptance status is recorded.
- The S11 milestone document exists and has been tested for reconstruction in a fresh session (section 1A).
