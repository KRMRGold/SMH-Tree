"""Unified search respects M4/M1 visibility boundaries."""
from fastapi.testclient import TestClient

from cogplat.config import Settings
from cogplat.main import create_app


def test_search_returns_claims_memory_and_only_visible_branch_messages(tmp_path):
    app = create_app(Settings(api_token="test-token", data_dir=tmp_path), providers={})
    client = TestClient(app)
    assert client.get("/v1/search?q=orchid").status_code == 401
    auth = {"Authorization": "Bearer test-token"}

    project = client.post(
        "/v1/projects", json={"name": "Botany"}, headers=auth
    ).json()
    conversation = client.post(
        "/v1/conversations",
        json={"title": "Orchid research", "project_id": project["id"]},
        headers=auth,
    ).json()
    root = conversation["root_branch_id"]

    inherited = client.post(
        f"/v1/branches/{root}/messages",
        json={"role": "user", "participant": "user", "content": "Orchid root observation"},
        headers=auth,
    ).json()
    child = client.post(
        "/v1/branches",
        json={
            "parent_branch_id": root,
            "fork_message_id": inherited["id"],
            "name": "Child",
        },
        headers=auth,
    ).json()["id"]
    later_parent = client.post(
        f"/v1/branches/{root}/messages",
        json={"role": "user", "participant": "user", "content": "Orchid parent-only update"},
        headers=auth,
    ).json()
    child_message = client.post(
        f"/v1/branches/{child}/messages",
        json={"role": "user", "participant": "user", "content": "Orchid child observation"},
        headers=auth,
    ).json()

    claim = client.post(
        "/v1/claims",
        json={
            "project_id": project["id"],
            "claim_type": "factual",
            "text": "Orchid roots need airflow",
        },
        headers=auth,
    ).json()
    memory = client.post(
        "/v1/memory",
        json={
            "scope": "project",
            "scope_id": project["id"],
            "kind": "fact",
            "content": "Orchid care notes mention airflow",
        },
        headers=auth,
    ).json()

    result = client.get(
        f"/v1/search?q=orchid&project_id={project['id']}&branch_id={child}",
        headers=auth,
    )
    assert result.status_code == 200
    items = result.json()["items"]
    types = {item["type"] for item in items}
    assert {"claim", "memory", "message"} <= types
    message_ids = {
        item["record"]["id"] for item in items if item["type"] == "message"
    }
    assert inherited["id"] in message_ids
    assert child_message["id"] in message_ids
    assert later_parent["id"] not in message_ids
    assert any(item["record"]["id"] == claim["id"] for item in items if item["type"] == "claim")
    assert any(item["record"]["id"] == memory["id"] for item in items if item["type"] == "memory")
