-- The ledger table was introduced in M0; M3 enforces append-only semantics.
CREATE TRIGGER remote_transmissions_no_update
BEFORE UPDATE ON remote_transmissions
BEGIN
    SELECT RAISE(ABORT, 'remote_transmissions is append-only');
END;

CREATE TRIGGER remote_transmissions_no_delete
BEFORE DELETE ON remote_transmissions
BEGIN
    SELECT RAISE(ABORT, 'remote_transmissions is append-only');
END;
