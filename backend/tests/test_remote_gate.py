"""Remote memory scope filtering tests."""
import json
from cogplat.db.connection import apply_migrations, connect_db
from cogplat.services.permissions import filter_remote_memory_items

def test_global_and_user_memory_are_stripped_by_default(tmp_path):
    connection = connect_db(tmp_path / "permissions.db")
    apply_migrations(connection)
    try:
        items = [{"id":"g1","scope":"global"},{"id":"u1","scope":"user"},{"id":"p1","scope":"project"},{"id":"b1","scope":"branch"}]
        retained, dropped = filter_remote_memory_items(connection, items)
        assert [item["id"] for item in retained] == ["p1", "b1"]
        assert dropped == ["g1", "u1"]
    finally:
        connection.close()

def test_global_and_user_memory_require_explicit_sharing_settings(tmp_path):
    connection = connect_db(tmp_path / "permissions-enabled.db")
    apply_migrations(connection)
    try:
        now = "2026-01-01T00:00:00Z"
        for scope in ("global", "user"):
            connection.execute(
                "INSERT INTO settings(key, value_json, updated_at) VALUES (?, ?, ?)",
                (f"share_{scope}_memory_remote", json.dumps(True), now),
            )
        retained, dropped = filter_remote_memory_items(connection, [{"id":"g1","scope":"global"},{"id":"u1","scope":"user"}])
        assert [item["id"] for item in retained] == ["g1", "u1"]
        assert dropped == []
    finally:
        connection.close()
