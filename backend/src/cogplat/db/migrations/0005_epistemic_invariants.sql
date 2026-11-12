-- M6 adds claim search and protects epistemic history without rewriting migration 0001.
CREATE VIRTUAL TABLE claims_fts USING fts5(
    text,
    content='claims',
    content_rowid='rowid'
);

CREATE TRIGGER claims_fts_insert AFTER INSERT ON claims BEGIN
    INSERT INTO claims_fts(rowid, text) VALUES (new.rowid, new.text);
END;

CREATE TRIGGER claims_fts_delete AFTER DELETE ON claims BEGIN
    INSERT INTO claims_fts(claims_fts, rowid, text)
    VALUES ('delete', old.rowid, old.text);
END;

CREATE TRIGGER claims_fts_update AFTER UPDATE ON claims BEGIN
    INSERT INTO claims_fts(claims_fts, rowid, text)
    VALUES ('delete', old.rowid, old.text);
    INSERT INTO claims_fts(rowid, text) VALUES (new.rowid, new.text);
END;

CREATE INDEX idx_claims_project_created ON claims(project_id, created_at, id);
CREATE INDEX idx_sources_project_created ON sources(project_id, created_at, id);
CREATE INDEX idx_claim_status_scope_latest
    ON claim_status_events(claim_id, scope, created_at DESC, id DESC);
CREATE INDEX idx_claim_assessments_latest
    ON claim_assessments(claim_id, dimension, created_at DESC, id DESC);
CREATE INDEX idx_claim_relations_pair
    ON claim_relations(from_claim_id, to_claim_id, rel);
CREATE INDEX idx_open_questions_project_state
    ON open_questions(project_id, state, created_at, id);

CREATE TRIGGER claims_no_update BEFORE UPDATE ON claims BEGIN
    SELECT RAISE(ABORT, 'claims are append-only');
END;
CREATE TRIGGER claims_no_delete BEFORE DELETE ON claims BEGIN
    SELECT RAISE(ABORT, 'claims are append-only');
END;

CREATE TRIGGER sources_no_update BEFORE UPDATE ON sources BEGIN
    SELECT RAISE(ABORT, 'sources are append-only');
END;
CREATE TRIGGER sources_no_delete BEFORE DELETE ON sources BEGIN
    SELECT RAISE(ABORT, 'sources are append-only');
END;

CREATE TRIGGER claim_status_events_no_update BEFORE UPDATE ON claim_status_events BEGIN
    SELECT RAISE(ABORT, 'claim status events are append-only');
END;
CREATE TRIGGER claim_status_events_no_delete BEFORE DELETE ON claim_status_events BEGIN
    SELECT RAISE(ABORT, 'claim status events are append-only');
END;

CREATE TRIGGER claim_assessments_no_update BEFORE UPDATE ON claim_assessments BEGIN
    SELECT RAISE(ABORT, 'claim assessments are append-only');
END;
CREATE TRIGGER claim_assessments_no_delete BEFORE DELETE ON claim_assessments BEGIN
    SELECT RAISE(ABORT, 'claim assessments are append-only');
END;

CREATE TRIGGER evidence_no_update BEFORE UPDATE ON evidence BEGIN
    SELECT RAISE(ABORT, 'evidence records are append-only');
END;
CREATE TRIGGER evidence_no_delete BEFORE DELETE ON evidence BEGIN
    SELECT RAISE(ABORT, 'evidence records are append-only');
END;

CREATE TRIGGER claim_relations_no_update BEFORE UPDATE ON claim_relations BEGIN
    SELECT RAISE(ABORT, 'claim relations are append-only');
END;
CREATE TRIGGER claim_relations_no_delete BEFORE DELETE ON claim_relations BEGIN
    SELECT RAISE(ABORT, 'claim relations are append-only');
END;
