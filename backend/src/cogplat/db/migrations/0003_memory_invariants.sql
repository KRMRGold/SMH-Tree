-- Enforce memory scope shape and supersession integrity at the database boundary.
CREATE TRIGGER memory_scope_shape_insert
BEFORE INSERT ON memory_items
WHEN
    (NEW.scope IN ('global', 'user') AND NEW.scope_id IS NOT NULL)
    OR (NEW.scope NOT IN ('global', 'user') AND NEW.scope_id IS NULL)
BEGIN
    SELECT RAISE(ABORT, 'invalid memory scope_id');
END;

CREATE TRIGGER memory_scope_shape_update
BEFORE UPDATE OF scope, scope_id ON memory_items
WHEN
    (NEW.scope IN ('global', 'user') AND NEW.scope_id IS NOT NULL)
    OR (NEW.scope NOT IN ('global', 'user') AND NEW.scope_id IS NULL)
BEGIN
    SELECT RAISE(ABORT, 'invalid memory scope_id');
END;

CREATE TRIGGER memory_supersession_insert
BEFORE INSERT ON memory_items
WHEN
    (NEW.state = 'superseded' AND (
        NEW.superseded_by IS NULL OR NOT EXISTS (
            SELECT 1 FROM memory_items replacement
            WHERE replacement.id = NEW.superseded_by
              AND replacement.scope = NEW.scope
              AND replacement.scope_id IS NEW.scope_id
              AND replacement.state = 'active'
        )
    ))
    OR (NEW.state <> 'superseded' AND NEW.superseded_by IS NOT NULL)
BEGIN
    SELECT RAISE(ABORT, 'invalid memory supersession');
END;

CREATE TRIGGER memory_supersession_update
BEFORE UPDATE OF state, superseded_by, scope, scope_id ON memory_items
WHEN
    (NEW.state = 'superseded' AND (
        NEW.superseded_by IS NULL OR NOT EXISTS (
            SELECT 1 FROM memory_items replacement
            WHERE replacement.id = NEW.superseded_by
              AND replacement.id <> NEW.id
              AND replacement.scope = NEW.scope
              AND replacement.scope_id IS NEW.scope_id
              AND replacement.state = 'active'
        )
    ))
    OR (NEW.state <> 'superseded' AND NEW.superseded_by IS NOT NULL)
BEGIN
    SELECT RAISE(ABORT, 'invalid memory supersession');
END;
