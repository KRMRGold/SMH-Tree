"""Chat SSE, persistence, error, auth, and cancellation tests."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from cogplat.config import Settings
from cogplat.db.connection import apply_migrations, connect_db
from cogplat.domain.chat import ChatMessage
from cogplat.main import create_app
from cogplat.providers.base import ProviderError
from cogplat.repos import runs as run_repo
from cogplat.services import chat as chat_service
from cogplat.services import conversations


class FakeProvider:
    label = "Fake"
    is_remote = False

    def __init__(self, tokens=None, fail=False, block=False):
        self.tokens = tokens or ["hello", " world"]
        self.fail = fail
        self.block = block
        self.called = False

    async def list_models(self):
        return ["fake-model"]

    async def stream_chat(self, model, messages, **opts):
        self.called = True
        for token in self.tokens:
            yield token
        if self.fail:
            raise ProviderError("fake provider failed")
        if self.block:
            await asyncio.Event().wait()

    async def embed(self, model, texts):
        raise NotImplementedError


def make_client(tmp_path, provider):
    app = create_app(
        Settings(api_token="test-token", data_dir=tmp_path),
        providers={"fake": provider},
    )
    return TestClient(app)


def auth():
    return {"Authorization": "Bearer test-token"}


def test_chat_streams_tokens_and_persists_one_assistant_message(tmp_path):
    provider = FakeProvider()
    client = make_client(tmp_path, provider)
    created = client.post("/v1/conversations", json={"title": "Chat"}, headers=auth()).json()
    branch_id = created["root_branch_id"]

    response = client.post(
        f"/v1/branches/{branch_id}/chat",
        json={"content": "Say hello", "provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert response.status_code == 200
    events = []
    current = None
    for line in response.text.splitlines():
        if line.startswith("event: "):
            current = line[7:]
        elif line.startswith("data: "):
            events.append((current, json.loads(line[6:])))
    assert [data["token"] for event, data in events if event == "token"] == ["hello", " world"]
    done = [data for event, data in events if event == "done"]
    assert len(done) == 1
    run_id = done[0]["run_id"]
    messages = client.get(f"/v1/branches/{branch_id}/messages", headers=auth()).json()["items"]
    assert [message["content"] for message in messages] == ["Say hello", "hello world"]
    assert sum(message["role"] == "assistant" for message in messages) == 1
    run = client.get(f"/v1/runs/{run_id}", headers=auth()).json()
    assert run["status"] == "succeeded"
    assert run["steps"][0]["status"] == "succeeded"
    assert client.get("/v1/transmissions", headers=auth()).json() == {"items": []}


def test_provider_error_emits_error_event_and_fails_run(tmp_path):
    provider = FakeProvider(fail=True)
    client = make_client(tmp_path, provider)
    branch_id = client.post("/v1/conversations", json={"title": "Chat"}, headers=auth()).json()["root_branch_id"]

    response = client.post(
        f"/v1/branches/{branch_id}/chat",
        json={"content": "Cause an error", "provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert "event: error" in response.text
    error_data = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")][-1]
    run = client.get(f"/v1/runs/{error_data['run_id']}", headers=auth()).json()
    assert run["status"] == "failed"
    assert run["steps"][0]["status"] == "failed"
    messages = client.get(f"/v1/branches/{branch_id}/messages", headers=auth()).json()["items"]
    assert [message["role"] for message in messages] == ["user"]


def test_remote_provider_is_not_called_without_explicit_allowance(tmp_path):
    provider = FakeProvider()
    provider.is_remote = True
    client = make_client(tmp_path, provider)
    branch_id = client.post("/v1/conversations", json={"title": "Chat"}, headers=auth()).json()["root_branch_id"]

    response = client.post(
        f"/v1/branches/{branch_id}/chat",
        json={"content": "Keep local", "provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert response.status_code == 403
    assert provider.called is False


def test_chat_endpoint_requires_authentication(tmp_path):
    client = make_client(tmp_path, FakeProvider())
    response = client.post(
        "/v1/branches/not-a-branch/chat",
        json={"content": "hello", "provider": "fake", "model": "fake-model"},
    )
    assert response.status_code == 401


def test_cancellation_marks_run_cancelled_and_does_not_persist_partial_assistant(tmp_path):
    connection = connect_db(tmp_path / "cancel.db")
    apply_migrations(connection)
    try:
        conversation = conversations.create_conversation(connection, "Cancellation")
        branch_id = str(conversation["root_branch_id"])
        provider = FakeProvider(tokens=["partial"], block=True)
        run, step, messages = chat_service.prepare_chat(
            connection, branch_id, "Question", "fake", "fake-model", False
        )

        async def exercise():
            stream = chat_service.stream_chat_events(
                connection, run, step, branch_id, "fake", provider,
                "fake-model", messages,
            )
            first = await anext(stream)
            assert first == ("token", {"run_id": run["id"], "token": "partial"})
            task = asyncio.create_task(anext(stream))
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(exercise())
        stored = run_repo.get_run(connection, str(run["id"]))
        assert stored["status"] == "cancelled"
        assert stored["steps"][0]["status"] == "cancelled"
        history = conversations.resolve_history(connection, branch_id)
        assert [message["role"] for message in history] == ["user"]
    finally:
        connection.close()


def test_provider_listing_and_model_discovery(tmp_path):
    client = make_client(tmp_path, FakeProvider())
    assert client.get("/v1/providers", headers=auth()).json()["items"][0]["id"] == "fake"
    assert client.get("/v1/providers/fake/models", headers=auth()).json()["items"] == ["fake-model"]


class AuditCheckingProvider(FakeProvider):
    is_remote = True
    def __init__(self, database_path):
        super().__init__(tokens=["remote reply"])
        self.database_path = database_path
        self.audit_visible_before_call = False
    async def stream_chat(self, model, messages, **opts):
        connection = connect_db(self.database_path)
        try:
            count = connection.execute("SELECT COUNT(*) FROM remote_transmissions").fetchone()[0]
            self.audit_visible_before_call = int(count) == 1
        finally:
            connection.close()
        self.called = True
        yield "remote reply"

def test_remote_allowed_is_audited_before_provider_call(tmp_path):
    provider = AuditCheckingProvider(tmp_path / "app.db")
    client = make_client(tmp_path, provider)
    branch_id = client.post("/v1/conversations", json={"title": "Remote"}, headers=auth()).json()["root_branch_id"]
    response = client.post(
        f"/v1/branches/{branch_id}/chat",
        json={"content": "Explicitly share this message", "provider": "fake", "model": "fake-model", "allow_remote": True},
        headers=auth(),
    )
    assert response.status_code == 200
    assert provider.called is True
    assert provider.audit_visible_before_call is True
    rows = client.get("/v1/transmissions", headers=auth()).json()["items"]
    assert len(rows) == 1
    assert rows[0]["provider_label"] == "Fake"
    assert len(rows[0]["item_refs"]) == 1
    assert rows[0]["byte_count"] > 0

def test_remote_gate_rejects_unapproved_run_before_provider_call(tmp_path):
    connection = connect_db(tmp_path / "gate.db")
    apply_migrations(connection)
    try:
        conversation = conversations.create_conversation(connection, "Gate")
        branch_id = str(conversation["root_branch_id"])
        provider = FakeProvider()
        provider.is_remote = True
        run, step, messages = chat_service.prepare_chat(connection, branch_id, "Do not send", "fake", "fake-model", False)
        async def exercise():
            events = [event async for event in chat_service.stream_chat_events(
                connection, run, step, branch_id, "fake", provider, "fake-model", messages
            )]
            assert events[-1][0] == "error"
        asyncio.run(exercise())
        assert provider.called is False
        assert connection.execute("SELECT COUNT(*) FROM remote_transmissions").fetchone()[0] == 0
    finally:
        connection.close()
