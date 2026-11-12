"""M5 deterministic context compiler and snapshot behavior tests."""

import pytest

from cogplat.config import Settings
from cogplat.db.connection import apply_migrations, connect_db
from cogplat.domain.context import (
    CompileRequest,
    ContextCompileError,
    DefaultTokenCounter,
)
from cogplat.domain.memory import MemoryCreate
from cogplat.main import create_app
from cogplat.repos import context_snapshots as snapshot_repo
from cogplat.services import chat as chat_service
from cogplat.services import context_compiler
from cogplat.services import conversations
from cogplat.services import memory as memory_service
from cogplat.services.permissions import build_access_context
from fastapi.testclient import TestClient


def make_db(path):
    connection = connect_db(path)
    apply_migrations(connection)
    return connection


def setup_branch(connection, project_description=None):
    with connection:
        connection.execute(
            "INSERT INTO projects(id, name, description, created_at) VALUES ('p1', 'Project', ?, '2026-01-01T00:00:00Z')",
            (project_description,),
        )
    conversation = conversations.create_conversation(connection, "Compiler", "p1")
    return str(conversation["root_branch_id"])


def test_compiler_is_deterministic_and_does_not_duplicate_current_message(tmp_path):
    connection = make_db(tmp_path / "compiler.db")
    try:
        branch_id = setup_branch(connection, "Project-specific context")
        conversations.append_message(connection, branch_id, "user", "user", "Earlier topic")
        memory = memory_service.create_memory(
            connection,
            MemoryCreate(
                scope="project", scope_id="p1", kind="preference",
                content="Prefer concise architecture explanations", importance=5,
            ),
        )
        current_id = "current-message"
        history = conversations.resolve_history(connection, branch_id) + [{
            "id": current_id, "role": "user", "content": "Current question about architecture"
        }]
        req = CompileRequest(
            access_context=build_access_context(connection, branch_id=branch_id),
            current_user_message="Current question about architecture",
            current_user_message_id=current_id,
            history=history,
            provider_id="local",
            provider_label="Local",
            provider_is_remote=False,
            model="test-model",
            max_input_tokens=2048,
            reserve_output_tokens=256,
        )
        first = context_compiler.compile_context(connection, req)
        second = context_compiler.compile_context(connection, req)
        assert first.to_dict() == second.to_dict()
        assert sum(
            message.role == "user" and message.content == "Current question about architecture"
            for message in first.messages
        ) == 1
        assert memory["id"] in first.source_refs
        assert first.messages[-1].content == "Current question about architecture"
        assert first.token_estimate <= first.input_budget
    finally:
        connection.close()


def test_oversized_user_message_is_head_tail_truncated_but_storage_is_unchanged(tmp_path):
    connection = make_db(tmp_path / "truncate.db")
    try:
        branch_id = setup_branch(connection)
        original = "BEGIN-" + ("middle " * 400) + "-ENDING"
        run, _step, messages = chat_service.prepare_chat(
            connection, branch_id, original, "local", "test-model", False,
            max_input_tokens=150, reserve_output_tokens=20,
        )
        user_message = messages[-1]
        assert user_message.role == "user"
        assert "characters omitted" in user_message.content
        assert user_message.content.startswith("BEGIN-")
        assert user_message.content.endswith("-ENDING")
        stored = conversations.resolve_history(connection, branch_id)
        assert stored[-1]["content"] == original
        snapshot = snapshot_repo.get_snapshot(connection, str(run["id"]))
        assert snapshot is not None
        assert snapshot["packet"]["transformations"][0]["type"] == "head_tail_truncation"
        assert snapshot["packet"]["token_estimate"] <= snapshot["packet"]["input_budget"]
    finally:
        connection.close()


def test_system_overflow_fails_run_before_snapshot_or_provider(tmp_path):
    connection = make_db(tmp_path / "system-overflow.db")
    try:
        branch_id = setup_branch(connection)
        with pytest.raises(ContextCompileError) as error:
            chat_service.prepare_chat(
                connection, branch_id, "Question", "local", "test-model", False,
                max_input_tokens=10, reserve_output_tokens=1,
            )
        assert error.value.code == "system_instructions_overflow"
        run = connection.execute(
            "SELECT id, status FROM runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        assert run["status"] == "failed"
        assert snapshot_repo.get_snapshot(connection, str(run["id"])) is None
    finally:
        connection.close()


def test_remote_packet_excludes_unshared_global_and_user_memory(tmp_path):
    connection = make_db(tmp_path / "remote-memory.db")
    try:
        branch_id = setup_branch(connection)
        global_item = memory_service.create_memory(
            connection, MemoryCreate(scope="global", kind="preference", content="Global private preference", importance=5)
        )
        user_item = memory_service.create_memory(
            connection, MemoryCreate(scope="user", kind="fact", content="User private fact", importance=5)
        )
        req = CompileRequest(
            access_context=build_access_context(connection, branch_id=branch_id, allow_remote=True),
            current_user_message="Tell me about this",
            current_user_message_id="current",
            history=[],
            provider_id="remote",
            provider_label="Remote",
            provider_is_remote=True,
            model="test-model",
            max_input_tokens=2048,
            reserve_output_tokens=256,
        )
        packet = context_compiler.compile_context(connection, req)
        assert global_item["id"] not in packet.source_refs
        assert user_item["id"] not in packet.source_refs
        excluded = {item["ref"]: item["reason"] for item in packet.excluded_sources}
        assert excluded[global_item["id"]] == "remote_sharing_disabled"
        assert excluded[user_item["id"]] == "remote_sharing_disabled"
    finally:
        connection.close()


def test_inspector_is_authenticated_and_returns_persisted_snapshot(tmp_path):
    provider = type("Provider", (), {
        "label": "Local", "is_remote": False,
        "list_models": lambda self: ["test-model"],
        "stream_chat": None,
        "embed": None,
    })()
    async def stream_chat(model, messages, **opts):
        yield "ok"
    provider.stream_chat = stream_chat
    app = create_app(
        Settings(api_token="test-token", data_dir=tmp_path),
        providers={"local": provider},
    )
    client = TestClient(app)
    auth = {"Authorization": "Bearer test-token"}
    branch_id = client.post(
        "/v1/conversations", json={"title": "Inspector"}, headers=auth
    ).json()["root_branch_id"]
    response = client.post(
        f"/v1/branches/{branch_id}/chat",
        json={"content": "Inspect this", "provider": "local", "model": "test-model"},
        headers=auth,
    )
    assert response.status_code == 200
    run_id = [
        __import__("json").loads(line[6:])["run_id"]
        for line in response.text.splitlines()
        if line.startswith("data: ") and "run_id" in line
    ][-1]
    assert client.get(f"/v1/runs/{run_id}/context").status_code == 401
    snapshot = client.get(f"/v1/runs/{run_id}/context", headers=auth)
    assert snapshot.status_code == 200
    assert snapshot.json()["packet"]["messages"][-1] == {
        "role": "user", "content": "Inspect this"
    }


def test_default_token_counter_uses_conservative_estimate():
    counter = DefaultTokenCounter()
    from cogplat.domain.chat import ChatMessage
    assert counter.count_messages([ChatMessage(role="user", content="1234567")]) == 6
