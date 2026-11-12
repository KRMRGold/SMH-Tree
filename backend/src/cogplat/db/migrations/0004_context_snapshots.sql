-- Context packets are immutable inspection records, one per compiled chat run.
CREATE UNIQUE INDEX idx_context_snapshots_run_unique
    ON context_snapshots(run_id);

CREATE TRIGGER context_snapshots_reject_update
BEFORE UPDATE ON context_snapshots
BEGIN
    SELECT RAISE(ABORT, 'context snapshots are immutable');
END;

CREATE TRIGGER context_snapshots_reject_delete
BEFORE DELETE ON context_snapshots
BEGIN
    SELECT RAISE(ABORT, 'context snapshots are immutable');
END;
