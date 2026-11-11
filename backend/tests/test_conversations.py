import sqlite3

import pytest

from cogplat.db.connection import apply_migrations, connect_db
from cogplat.domain.ids import is_uuid7, new_id
from cogplat.services import conversations


@pytest.fixture
def db(tmp_path):
    connection = connect_db(tmp_path / "app.db")
    apply_migrations(connection)
    try:
        yield connection
    finally:
        connection.close()


def make_conversation(db):
    conversation = conversations.create_conversation(db, "Test conversation")
    return conversation, str(conversation["root_branch_id"])


def add(db, branch_id, content):
    return conversations.append_message(
        db, branch_id, "user", "user", content
    )


def contents(messages):
    return [message["content"] for message in messages]


def test_uuid_generator_emits_uuid7():
    generated = [new_id() for _ in range(100)]
    assert all(is_uuid7(value) for value in generated)
    assert len(set(generated)) == len(generated)


def test_linear_history_is_in_sequence(db):
    _, root = make_conversation(db)
    add(db, root, "one")
    add(db, root, "two")
    add(db, root, "three")

    assert contents(conversations.resolve_history(db, root)) == [
        "one", "two", "three"
    ]


def test_fork_inherits_only_through_fork_message(db):
    _, root = make_conversation(db)
    first = add(db, root, "one")
    add(db, root, "two")
    child = conversations.fork_branch(db, root, str(first["id"]), "Alternative")
    add(db, str(child["id"]), "child")

    assert contents(conversations.resolve_history(db, str(child["id"]))) == [
        "one", "child"
    ]


def test_parent_messages_added_after_fork_are_not_visible(db):
    _, root = make_conversation(db)
    first = add(db, root, "before fork")
    child = conversations.fork_branch(db, root, str(first["id"]), "Child")
    add(db, root, "after fork")

    assert contents(conversations.resolve_history(db, str(child["id"]))) == [
        "before fork"
    ]


def test_sibling_branch_messages_are_never_visible(db):
    _, root = make_conversation(db)
    first = add(db, root, "shared")
    left = conversations.fork_branch(db, root, str(first["id"]), "Left")
    right = conversations.fork_branch(db, root, str(first["id"]), "Right")
    add(db, str(left["id"]), "left only")
    add(db, str(right["id"]), "right only")

    assert contents(conversations.resolve_history(db, str(left["id"]))) == [
        "shared", "left only"
    ]
    assert contents(conversations.resolve_history(db, str(right["id"]))) == [
        "shared", "right only"
    ]


def test_fork_of_fork_resolves_in_order(db):
    _, root = make_conversation(db)
    first = add(db, root, "root one")
    add(db, root, "root two")
    child = conversations.fork_branch(db, root, str(first["id"]), "Child")
    child_message = add(db, str(child["id"]), "child one")
    add(db, str(child["id"]), "child two")
    grandchild = conversations.fork_branch(
        db, str(child["id"]), str(child_message["id"]), "Grandchild"
    )
    add(db, str(grandchild["id"]), "grandchild one")

    assert contents(conversations.resolve_history(db, str(grandchild["id"]))) == [
        "root one", "child one", "grandchild one"
    ]


def test_fork_can_target_message_inherited_from_ancestor(db):
    _, root = make_conversation(db)
    root_first = add(db, root, "root first")
    add(db, root, "root second")
    child = conversations.fork_branch(db, root, str(root_first["id"]), "Child")
    add(db, str(child["id"]), "child message")
    grandchild = conversations.fork_branch(
        db, str(child["id"]), str(root_first["id"]), "Earlier fork"
    )
    add(db, str(grandchild["id"]), "grandchild message")

    assert contents(conversations.resolve_history(db, str(grandchild["id"]))) == [
        "root first", "grandchild message"
    ]


def test_fork_rejects_message_not_visible_in_parent(db):
    _, root = make_conversation(db)
    first = add(db, root, "root")
    child = conversations.fork_branch(db, root, str(first["id"]), "Child")
    other = add(db, str(child["id"]), "child-only")
    with pytest.raises(conversations.InvalidFork):
        conversations.fork_branch(db, root, str(other["id"]), "Invalid")


def test_deep_branch_chain_of_fifty_resolves_without_recursion(db):
    _, root = make_conversation(db)
    latest = add(db, root, "level 0")
    parent_id = root

    for depth in range(1, 51):
        child = conversations.fork_branch(
            db, parent_id, str(latest["id"]), f"Level {depth}"
        )
        parent_id = str(child["id"])
        latest = add(db, parent_id, f"level {depth}")

    history = conversations.resolve_history(db, parent_id)
    assert len(history) == 51
    assert contents(history) == [f"level {i}" for i in range(51)]


def test_message_sequence_uniqueness_is_enforced_by_sqlite(db):
    _, root = make_conversation(db)
    message = add(db, root, "first")

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO messages(id, branch_id, seq, role, participant, content, created_at) "
            "VALUES (?, ?, ?, 'user', 'user', 'duplicate', '2026-01-01T00:00:00Z')",
            (new_id(), root, message["seq"]),
        )


def test_projects_and_conversations_are_scoped(db):
    project = conversations.create_project(db, "Project", "Description")
    conversation = conversations.create_conversation(
        db, "Inside project", str(project["id"])
    )
    assert conversations.list_projects(db)[0]["id"] == project["id"]
    assert conversations.list_conversations(db, str(project["id"]))[0]["id"] == conversation["id"]
    assert conversations.list_branches(db, str(conversation["id"]))[0]["id"] == conversation["root_branch_id"]


def test_missing_project_prevents_conversation_creation(db):
    with pytest.raises(conversations.ResourceNotFound):
        conversations.create_conversation(db, "Orphan", "missing-project")
    assert conversations.list_conversations(db) == []
