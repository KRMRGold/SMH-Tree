import json
import pytest
from cogplat.db.connection import apply_migrations, connect_db
from cogplat.domain.memory import MemoryCreate, MemoryLifecycleUpdate
from cogplat.services import memory as memory_service
from cogplat.services.permissions import build_access_context

def make_db(path):
    connection = connect_db(path)
    apply_migrations(connection)
    return connection

def insert_scope_graph(connection):
    connection.execute("INSERT INTO projects(id, name, created_at) VALUES ('p1', 'Project', '2026-01-01T00:00:00Z')")
    connection.execute("INSERT INTO projects(id, name, created_at) VALUES ('p2', 'Other', '2026-01-01T00:00:00Z')")
    connection.execute("INSERT INTO conversations(id, project_id, title, created_at) VALUES ('c1', 'p1', 'Conversation', '2026-01-01T00:00:00Z')")
    connection.execute("INSERT INTO conversations(id, project_id, title, created_at) VALUES ('c2', 'p2', 'Other conversation', '2026-01-01T00:00:00Z')")
    connection.execute("INSERT INTO branches(id, conversation_id, name, created_at) VALUES ('root', 'c1', 'Root', '2026-01-01T00:00:00Z')")
    connection.execute("INSERT INTO messages(id, branch_id, seq, role, participant, content, created_at) VALUES ('fork-msg', 'root', 1, 'user', 'user', 'fork point', '2026-01-01T00:00:02Z')")
    connection.execute("INSERT INTO branches(id, conversation_id, parent_branch_id, fork_message_id, name, created_at) VALUES ('child', 'c1', 'root', 'fork-msg', 'Child', '2026-01-01T00:00:03Z')")
    connection.execute("INSERT INTO branches(id, conversation_id, parent_branch_id, fork_message_id, name, created_at) VALUES ('sibling', 'c1', 'root', 'fork-msg', 'Sibling', '2026-01-01T00:00:03Z')")

def insert_memory(connection, memory_id, scope, scope_id, created_at, content=None):
    connection.execute(
        "INSERT INTO memory_items (id, scope, scope_id, kind, content, importance, state, origin_kind, created_at, updated_at) "
        "VALUES (?, ?, ?, 'fact', ?, 3, 'active', 'user', ?, ?)",
        (memory_id, scope, scope_id, content or memory_id, created_at, created_at),
    )

def test_scope_eligibility_includes_ancestor_at_fork_cutoff_and_excludes_siblings(tmp_path):
    connection = make_db(tmp_path / "scopes.db")
    try:
        insert_scope_graph(connection)
        insert_memory(connection, "global", "global", None, "2026-01-01T00:00:01Z")
        insert_memory(connection, "user", "user", None, "2026-01-01T00:00:01Z")
        insert_memory(connection, "project", "project", "p1", "2026-01-01T00:00:01Z")
        insert_memory(connection, "wrong-project", "project", "p2", "2026-01-01T00:00:01Z")
        insert_memory(connection, "conversation", "conversation", "c1", "2026-01-01T00:00:01Z")
        insert_memory(connection, "wrong-conversation", "conversation", "c2", "2026-01-01T00:00:01Z")
        insert_memory(connection, "root-before", "branch", "root", "2026-01-01T00:00:01Z")
        insert_memory(connection, "root-at-cutoff", "branch", "root", "2026-01-01T00:00:02Z")
        insert_memory(connection, "root-after", "branch", "root", "2026-01-01T00:00:03Z")
        insert_memory(connection, "child-own", "branch", "child", "2026-01-01T00:00:04Z")
        insert_memory(connection, "sibling-own", "branch", "sibling", "2026-01-01T00:00:04Z")
        insert_memory(connection, "agent-own", "agent", "agent-1", "2026-01-01T00:00:04Z")
        insert_memory(connection, "other-agent", "agent", "agent-2", "2026-01-01T00:00:04Z")
        context = build_access_context(connection, branch_id="child", agent_id="agent-1")
        found = {item["id"] for item in memory_service.list_memory(connection, context)}
        assert found == {
            "global", "user", "project", "conversation",
            "root-before", "root-at-cutoff", "child-own", "agent-own",
        }
    finally:
        connection.close()

def test_remote_context_excludes_global_and_user_until_explicitly_enabled(tmp_path):
    connection = make_db(tmp_path / "remote.db")
    try:
        insert_memory(connection, "g1", "global", None, "2026-01-01T00:00:00Z")
        insert_memory(connection, "u1", "user", None, "2026-01-01T00:00:00Z")
        context = build_access_context(connection, allow_remote=True)
        assert memory_service.list_memory(connection, context) == []
        now = "2026-01-01T00:00:00Z"
        for scope in ("global", "user"):
            connection.execute(
                "INSERT INTO settings(key, value_json, updated_at) VALUES (?, ?, ?)",
                (f"share_{scope}_memory_remote", json.dumps(True), now),
            )
        assert {item["id"] for item in memory_service.list_memory(connection, context)} == {"g1", "u1"}
    finally:
        connection.close()

def test_fts_search_and_supersede_preserve_original_item(tmp_path):
    connection = make_db(tmp_path / "lifecycle.db")
    try:
        original = memory_service.create_memory(
            connection, MemoryCreate(scope="global", kind="preference", content="Use copper lanterns", importance=5)
        )
        replacement = memory_service.create_memory(
            connection, MemoryCreate(scope="global", kind="preference", content="Use brass lanterns", importance=5)
        )
        hits = memory_service.list_memory(connection, build_access_context(connection), query="copper lantern")
        assert [item["id"] for item in hits] == [original["id"]]
        superseded = memory_service.update_memory_lifecycle(
            connection, original["id"],
            MemoryLifecycleUpdate(state="superseded", superseded_by=replacement["id"]),
        )
        assert superseded["state"] == "superseded"
        assert superseded["content"] == "Use copper lanterns"
        assert [item["id"] for item in memory_service.list_memory(connection, build_access_context(connection))] == [replacement["id"]]
        all_items = memory_service.list_memory(connection, build_access_context(connection), state="all")
        assert {item["id"] for item in all_items} == {original["id"], replacement["id"]}
    finally:
        connection.close()

def test_supersession_requires_same_scope_and_active_replacement(tmp_path):
    connection = make_db(tmp_path / "invalid-supersede.db")
    try:
        original = memory_service.create_memory(connection, MemoryCreate(scope="global", kind="fact", content="Old"))
        other_scope = memory_service.create_memory(connection, MemoryCreate(scope="user", kind="fact", content="New"))
        with pytest.raises(memory_service.InvalidMemoryTransition):
            memory_service.update_memory_lifecycle(
                connection, original["id"],
                MemoryLifecycleUpdate(state="superseded", superseded_by=other_scope["id"]),
            )
        with pytest.raises(ValueError):
            MemoryLifecycleUpdate(state="superseded")
    finally:
        connection.close()

def test_outdated_memory_is_not_selected_or_rewritten(tmp_path):
    connection = make_db(tmp_path / "outdated.db")
    try:
        item = memory_service.create_memory(connection, MemoryCreate(scope="global", kind="fact", content="Original fact"))
        updated = memory_service.update_memory_lifecycle(
            connection, item["id"], MemoryLifecycleUpdate(state="outdated")
        )
        assert updated["state"] == "outdated"
        assert updated["content"] == "Original fact"
        assert memory_service.list_memory(connection, build_access_context(connection)) == []
        with pytest.raises(memory_service.InvalidMemoryTransition):
            memory_service.update_memory_lifecycle(
                connection, item["id"], MemoryLifecycleUpdate(state="outdated")
            )
    finally:
        connection.close()

def test_database_rejects_invalid_scope_shape_and_supersession(tmp_path):
    connection = make_db(tmp_path / "constraints.db")
    try:
        with pytest.raises(Exception, match="invalid memory scope_id"):
            connection.execute(
                "INSERT INTO memory_items (id, scope, scope_id, kind, content, origin_kind, created_at, updated_at) "
                "VALUES ('bad', 'global', 'not-null', 'fact', 'Bad', 'user', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
            )
        with pytest.raises(Exception, match="invalid memory supersession"):
            connection.execute(
                "INSERT INTO memory_items (id, scope, scope_id, kind, content, state, origin_kind, created_at, updated_at) "
                "VALUES ('bad2', 'global', NULL, 'fact', 'Bad', 'superseded', 'user', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
            )
    finally:
        connection.close()
