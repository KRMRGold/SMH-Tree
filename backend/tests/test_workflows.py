"""M7 checkpointed chat and explicit claim extraction workflows."""

import json
import sqlite3

from fastapi.testclient import TestClient

from cogplat.config import Settings
from cogplat.main import create_app


class FakeProvider:
    label = "Workflow fake"
    is_remote = False

    def __init__(self, output="hello world", remote=False, fail_once=False):
        self.output = output
        self.is_remote = remote
        self.called = False
        self.fail_once = fail_once
        self.calls = 0

    async def list_models(self, **opts):
        return ["fake-model"]

    async def stream_chat(self, model, messages, **opts):
        self.called = True
        self.calls += 1
        if self.fail_once and self.calls == 1:
            yield "temporary partial"
            raise RuntimeError("temporary provider failure")
        yield self.output

    async def embed(self, model, texts):
        raise NotImplementedError


def client_for(tmp_path, provider, *, workflows_enabled=True):
    app = create_app(
        Settings(
            api_token="test-token",
            data_dir=tmp_path,
            workflows_enabled=workflows_enabled,
        ),
        providers={"fake": provider},
    )
    return TestClient(app)


def auth():
    return {"Authorization": "Bearer test-token"}


def create_message(client):
    conversation = client.post(
        "/v1/conversations", json={"title": "Extraction"}, headers=auth()
    ).json()
    branch_id = conversation["root_branch_id"]
    response = client.post(
        f"/v1/branches/{branch_id}/messages",
        json={
            "role": "user",
            "participant": "user",
            "content": "The moon orbits Earth. Earth has one natural moon.",
        },
        headers=auth(),
    )
    assert response.status_code == 201
    return response.json()


def test_chat_uses_checkpointed_graph_and_preserves_sse_contract(tmp_path):
    provider = FakeProvider("hello world")
    client = client_for(tmp_path, provider)
    conversation = client.post(
        "/v1/conversations", json={"title": "Graph chat"}, headers=auth()
    ).json()
    response = client.post(
        f"/v1/branches/{conversation['root_branch_id']}/chat",
        json={"content": "Say hello", "provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert response.status_code == 200
    assert "event: token\ndata:" in response.text
    assert "event: done\ndata:" in response.text
    done = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ") and "run_id" in line
    ][-1]
    assert done["message"]["content"] == "hello world"
    connection = sqlite3.connect(tmp_path / "app.db")
    try:
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "checkpoints" in tables
        assert connection.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?",
            (done["run_id"],),
        ).fetchone()[0] >= 1
    finally:
        connection.close()


def test_explicit_extraction_persists_proposed_claims_and_provenance(tmp_path):
    output = json.dumps({
        "claims": [
            {
                "claim_type": "factual",
                "text": "The moon orbits Earth.",
                "evidence_excerpt": "The moon orbits Earth.",
            }
        ]
    })
    client = client_for(tmp_path, FakeProvider(output))
    message = create_message(client)
    response = client.post(
        f"/v1/messages/{message['id']}/extract-claims",
        json={"provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["claim_ids"]) == 1
    claim = client.get(
        f"/v1/claims/{result['claim_ids'][0]}", headers=auth()
    ).json()
    assert claim["origin_kind"] == "extraction"
    assert claim["origin_ref"] == message["id"]
    assert claim["current_status"][0]["status"] == "proposed"
    assert claim["evidence"][0]["stance"] == "context"
    assert claim["evidence"][0]["excerpt"] == "The moon orbits Earth."
    connection = sqlite3.connect(tmp_path / "app.db")
    try:
        links = connection.execute(
            "SELECT to_type, to_id, rel FROM links WHERE from_type='claim' AND from_id=?",
            (claim["id"],),
        ).fetchall()
        assert ("message", message["id"], "derived_from") in links
        assert ("run", result["run_id"], "produced_by") in links
    finally:
        connection.close()


def test_invalid_or_nonverbatim_extraction_writes_no_claims(tmp_path):
    output = json.dumps({
        "claims": [{
            "claim_type": "factual",
            "text": "A fabricated statement.",
            "evidence_excerpt": "This text is not in the source.",
        }]
    })
    client = client_for(tmp_path, FakeProvider(output))
    message = create_message(client)
    response = client.post(
        f"/v1/messages/{message['id']}/extract-claims",
        json={"provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert response.status_code == 422
    assert client.get("/v1/claims", headers=auth()).json()["items"] == []


def test_remote_extraction_requires_explicit_opt_in(tmp_path):
    provider = FakeProvider("{}", remote=True)
    client = client_for(tmp_path, provider)
    message = create_message(client)
    response = client.post(
        f"/v1/messages/{message['id']}/extract-claims",
        json={"provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert response.status_code == 403
    assert provider.called is False


def test_disabling_workflows_keeps_legacy_chat_and_disables_extraction(tmp_path):
    provider = FakeProvider("legacy reply")
    client = client_for(tmp_path, provider, workflows_enabled=False)
    conversation = client.post(
        "/v1/conversations", json={"title": "Legacy"}, headers=auth()
    ).json()
    response = client.post(
        f"/v1/branches/{conversation['root_branch_id']}/chat",
        json={"content": "Use fallback", "provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert response.status_code == 200
    assert "event: done" in response.text
    message = create_message(client)
    extraction = client.post(
        f"/v1/messages/{message['id']}/extract-claims",
        json={"provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert extraction.status_code == 503
    assert client.get("/v1/health", headers=auth()).json()["capabilities"]["workflows"] is False



def test_failed_chat_node_resumes_from_checkpoint_without_recompiling(tmp_path):
    provider = FakeProvider("complete response", fail_once=True)
    client = client_for(tmp_path, provider)
    conversation = client.post(
        "/v1/conversations", json={"title": "Resume"}, headers=auth()
    ).json()
    branch_id = conversation["root_branch_id"]
    first = client.post(
        f"/v1/branches/{branch_id}/chat",
        json={"content": "Resume this turn", "provider": "fake", "model": "fake-model"},
        headers=auth(),
    )
    assert "event: error" in first.text
    run_id = [
        json.loads(line[6:])["run_id"]
        for line in first.text.splitlines()
        if line.startswith("data: ") and "run_id" in line
    ][-1]
    resumed = client.post(f"/v1/runs/{run_id}/resume", headers=auth())
    assert resumed.status_code == 200
    assert "event: done" in resumed.text
    assert provider.calls == 2
    history = client.get(
        f"/v1/branches/{branch_id}/messages", headers=auth()
    ).json()["items"]
    assert [item["role"] for item in history] == ["user", "assistant"]
    assert history[-1]["content"] == "complete response"
    connection = sqlite3.connect(tmp_path / "app.db")
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM context_snapshots WHERE run_id = ?", (run_id,)
        ).fetchone()[0] == 1
    finally:
        connection.close()
