-- Initial canonical schema. Keep this migration immutable after it is applied.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    title TEXT NOT NULL,
    root_branch_id TEXT,
    created_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE branches (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    parent_branch_id TEXT REFERENCES branches(id),
    fork_message_id TEXT REFERENCES messages(id),
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK ((parent_branch_id IS NULL) = (fork_message_id IS NULL))
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    branch_id TEXT NOT NULL REFERENCES branches(id),
    seq INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    participant TEXT NOT NULL,
    content TEXT NOT NULL,
    model_ref TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (branch_id, seq)
);

CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='rowid'
);

CREATE TRIGGER messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER messages_fts_delete AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content)
    VALUES ('delete', old.rowid, old.content);
END;

CREATE TRIGGER messages_fts_update AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content)
    VALUES ('delete', old.rowid, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TABLE memory_items (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL CHECK (scope IN ('global', 'user', 'project', 'conversation', 'branch', 'agent')),
    scope_id TEXT,
    kind TEXT NOT NULL CHECK (kind IN ('preference', 'fact', 'decision', 'goal', 'procedure', 'open_question', 'pattern')),
    content TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
    state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'outdated', 'superseded', 'archived')),
    superseded_by TEXT REFERENCES memory_items(id),
    origin_kind TEXT NOT NULL CHECK (origin_kind IN ('user', 'agent', 'extraction', 'import')),
    origin_ref TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE memory_fts USING fts5(
    content,
    content='memory_items',
    content_rowid='rowid'
);

CREATE TRIGGER memory_fts_insert AFTER INSERT ON memory_items BEGIN
    INSERT INTO memory_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER memory_fts_delete AFTER DELETE ON memory_items BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, content)
    VALUES ('delete', old.rowid, old.content);
END;

CREATE TRIGGER memory_fts_update AFTER UPDATE ON memory_items BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, content)
    VALUES ('delete', old.rowid, old.content);
    INSERT INTO memory_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    kind TEXT NOT NULL CHECK (kind IN ('document', 'url', 'message', 'user_statement', 'agent_output', 'dataset')),
    title TEXT,
    uri TEXT,
    content_hash TEXT,
    retrieved_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE claims (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    claim_type TEXT NOT NULL CHECK (claim_type IN ('factual', 'causal', 'normative', 'predictive', 'definition', 'other')),
    text TEXT NOT NULL,
    subject TEXT,
    predicate TEXT,
    object TEXT,
    valid_from TEXT,
    valid_to TEXT,
    origin_kind TEXT NOT NULL CHECK (origin_kind IN ('user', 'agent', 'extraction', 'import')),
    origin_ref TEXT,
    observed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE claim_status_events (
    id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(id),
    status TEXT NOT NULL CHECK (status IN ('proposed', 'reported', 'inferred', 'corroborated', 'contested', 'accepted', 'rejected', 'superseded', 'unresolved', 'unknown')),
    scope TEXT NOT NULL DEFAULT 'default',
    policy TEXT,
    rationale TEXT,
    actor_kind TEXT NOT NULL CHECK (actor_kind IN ('user', 'agent', 'system')),
    actor_ref TEXT,
    created_at TEXT NOT NULL,
    CHECK (status <> 'accepted' OR policy IS NOT NULL)
);

CREATE TABLE claim_assessments (
    id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(id),
    dimension TEXT NOT NULL CHECK (dimension IN ('source_reliability', 'evidence_strength', 'extraction_reliability', 'verification_status', 'temporal_validity', 'argument_strength')),
    value_num REAL CHECK (value_num BETWEEN 0 AND 1),
    value_text TEXT,
    rationale TEXT,
    actor_kind TEXT NOT NULL,
    actor_ref TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE evidence (
    id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(id),
    source_id TEXT NOT NULL REFERENCES sources(id),
    stance TEXT NOT NULL CHECK (stance IN ('supports', 'challenges', 'context')),
    excerpt TEXT,
    locator TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE claim_relations (
    id TEXT PRIMARY KEY,
    from_claim_id TEXT NOT NULL REFERENCES claims(id),
    to_claim_id TEXT NOT NULL REFERENCES claims(id),
    rel TEXT NOT NULL CHECK (rel IN ('contradicts', 'supports', 'supersedes', 'refines', 'depends_on')),
    contradiction_basis TEXT CHECK (contradiction_basis IN ('direct', 'different_time', 'different_context', 'different_definition', 'unclear')),
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE open_questions (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    text TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'investigating', 'answered', 'dropped')),
    related_claim_id TEXT REFERENCES claims(id),
    created_at TEXT NOT NULL
);

CREATE TABLE links (
    id TEXT PRIMARY KEY,
    from_type TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_type TEXT NOT NULL,
    to_id TEXT NOT NULL,
    rel TEXT NOT NULL,
    created_by_kind TEXT NOT NULL,
    created_by_ref TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (from_type, from_id, to_type, to_id, rel)
);
CREATE INDEX links_from ON links(from_type, from_id);
CREATE INDEX links_to ON links(to_type, to_id);

CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    conversation_id TEXT,
    branch_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')),
    allow_remote INTEGER NOT NULL DEFAULT 0 CHECK (allow_remote IN (0, 1)),
    input_json TEXT,
    output_json TEXT,
    error TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE run_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    seq INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    detail_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (run_id, seq)
);

CREATE TABLE provider_configs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('ollama', 'openai_compat')),
    label TEXT NOT NULL,
    base_url TEXT NOT NULL,
    is_remote INTEGER NOT NULL CHECK (is_remote IN (0, 1)),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
);

CREATE TABLE context_snapshots (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    provider_label TEXT NOT NULL,
    packet_json TEXT NOT NULL,
    token_estimate INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE remote_transmissions (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    provider_label TEXT NOT NULL,
    item_refs_json TEXT NOT NULL,
    byte_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_branches_conversation ON branches(conversation_id);
CREATE INDEX idx_branches_parent ON branches(parent_branch_id);
CREATE INDEX idx_messages_branch_seq ON messages(branch_id, seq);
CREATE INDEX idx_memory_scope_state ON memory_items(scope, scope_id, state);
CREATE INDEX idx_claim_status_claim_scope ON claim_status_events(claim_id, scope, created_at);
CREATE INDEX idx_evidence_claim ON evidence(claim_id);
CREATE INDEX idx_claim_relations_from ON claim_relations(from_claim_id);
CREATE INDEX idx_claim_relations_to ON claim_relations(to_claim_id);
CREATE INDEX idx_runs_conversation_branch ON runs(conversation_id, branch_id);
CREATE INDEX idx_run_steps_run_seq ON run_steps(run_id, seq);
CREATE INDEX idx_context_snapshots_run ON context_snapshots(run_id);
CREATE INDEX idx_remote_transmissions_run ON remote_transmissions(run_id);
