import sqlite3

import pytest

from cogplat.db.connection import apply_migrations, connect_db

EXPECTED_TABLES = {
    "schema_migrations",
    "projects",
    "conversations",
    "branches",
    "messages",
    "messages_fts",
    "memory_items",
    "memory_fts",
    "sources",
    "claims",
    "claim_status_events",
    "claim_assessments",
    "evidence",
    "claim_relations",
    "open_questions",
    "links",
    "runs",
    "run_steps",
    "provider_configs",
    "context_snapshots",
    "remote_transmissions",
    "settings",
}


def open_migrated_db(path):
    connection = connect_db(path)
    apply_migrations(connection)
    return connection


def test_migration_applies_once_and_is_idempotent(tmp_path):
    connection = connect_db(tmp_path / "app.db")
    try:
        assert apply_migrations(connection) == 4
        first = connection.execute(
            "SELECT version, applied_at FROM schema_migrations"
        ).fetchall()

        assert apply_migrations(connection) == 4
        second = connection.execute(
            "SELECT version, applied_at FROM schema_migrations"
        ).fetchall()

        assert len(first) == 4
        assert [tuple(row) for row in second] == [tuple(row) for row in first]
    finally:
        connection.close()


def test_all_section_four_tables_exist(tmp_path):
    connection = open_migrated_db(tmp_path / "app.db")
    try:
        actual = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "AND name NOT LIKE '%_fts_%'"
            )
        }
        assert actual == EXPECTED_TABLES
    finally:
        connection.close()


def test_foreign_keys_are_enabled_and_enforced(tmp_path):
    connection = open_migrated_db(tmp_path / "app.db")
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO branches "
                "(id, conversation_id, parent_branch_id, fork_message_id, name, created_at) "
                "VALUES ('branch-1', 'missing-conversation', NULL, NULL, 'root', '2026-01-01T00:00:00Z')"
            )
    finally:
        connection.close()


def test_wal_mode_is_enabled(tmp_path):
    connection = connect_db(tmp_path / "app.db")
    try:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        connection.close()


def test_fts_tables_track_messages_and_memory(tmp_path):
    connection = open_migrated_db(tmp_path / "app.db")
    try:
        connection.execute(
            "INSERT INTO projects(id, name, created_at) VALUES ('p1', 'Project', '2026-01-01T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO conversations(id, project_id, title, created_at) "
            "VALUES ('c1', 'p1', 'Conversation', '2026-01-01T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO branches(id, conversation_id, name, created_at) "
            "VALUES ('b1', 'c1', 'Root', '2026-01-01T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO messages(id, branch_id, seq, role, participant, content, created_at) "
            "VALUES ('m1', 'b1', 1, 'user', 'user', 'branching memory architecture', '2026-01-01T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO memory_items(id, scope, kind, content, origin_kind, created_at, updated_at) "
            "VALUES ('mem1', 'global', 'fact', 'persistent cognitive memory', 'user', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )

        message_hits = connection.execute(
            "SELECT rowid FROM messages_fts WHERE messages_fts MATCH 'branching'"
        ).fetchall()
        memory_hits = connection.execute(
            "SELECT rowid FROM memory_fts WHERE memory_fts MATCH 'cognitive'"
        ).fetchall()
        assert len(message_hits) == 1
        assert len(memory_hits) == 1
    finally:
        connection.close()


def test_remote_transmission_audit_is_append_only(tmp_path):
    connection = open_migrated_db(tmp_path / "audit.db")
    try:
        connection.execute("INSERT INTO projects(id, name, created_at) VALUES ('p1', 'Project', '2026-01-01T00:00:00Z')")
        connection.execute("INSERT INTO conversations(id, project_id, title, created_at) VALUES ('c1', 'p1', 'Conversation', '2026-01-01T00:00:00Z')")
        connection.execute("INSERT INTO branches(id, conversation_id, name, created_at) VALUES ('b1', 'c1', 'Root', '2026-01-01T00:00:00Z')")
        connection.execute("INSERT INTO runs(id, kind, conversation_id, branch_id, status, created_at) VALUES ('r1', 'chat_turn', 'c1', 'b1', 'succeeded', '2026-01-01T00:00:00Z')")
        connection.execute("INSERT INTO remote_transmissions(id, run_id, provider_label, item_refs_json, byte_count, created_at) VALUES ('t1', 'r1', 'Remote', '[]', 2, '2026-01-01T00:00:00Z')")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE remote_transmissions SET byte_count = 3 WHERE id = 't1'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM remote_transmissions WHERE id = 't1'")
    finally:
        connection.close()



def test_context_snapshots_are_unique_per_run_and_immutable(tmp_path):
    connection = open_migrated_db(tmp_path / "snapshots.db")
    try:
        connection.execute("INSERT INTO projects(id, name, created_at) VALUES ('p1', 'Project', '2026-01-01T00:00:00Z')")
        connection.execute("INSERT INTO conversations(id, project_id, title, created_at) VALUES ('c1', 'p1', 'Conversation', '2026-01-01T00:00:00Z')")
        connection.execute("INSERT INTO branches(id, conversation_id, name, created_at) VALUES ('b1', 'c1', 'Root', '2026-01-01T00:00:00Z')")
        connection.execute("INSERT INTO runs(id, kind, conversation_id, branch_id, status, created_at) VALUES ('r1', 'chat_turn', 'c1', 'b1', 'running', '2026-01-01T00:00:00Z')")
        connection.execute("INSERT INTO context_snapshots(id, run_id, provider_label, packet_json, token_estimate, created_at) VALUES ('s1', 'r1', 'Local', '{}', 10, '2026-01-01T00:00:00Z')")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO context_snapshots(id, run_id, provider_label, packet_json, token_estimate, created_at) VALUES ('s2', 'r1', 'Local', '{}', 10, '2026-01-01T00:00:01Z')")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("UPDATE context_snapshots SET token_estimate = 11 WHERE id = 's1'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM context_snapshots WHERE id = 's1'")
    finally:
        connection.close()
