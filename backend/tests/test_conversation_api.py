from fastapi.testclient import TestClient

from cogplat.config import Settings
from cogplat.main import create_app


def client_for(tmp_path):
    app = create_app(Settings(api_token="api-test-token", data_dir=tmp_path))
    return TestClient(app)


def auth():
    return {"Authorization": "Bearer api-test-token"}


def test_projects_conversations_and_branching_api(tmp_path):
    client = client_for(tmp_path)

    project_response = client.post(
        "/v1/projects",
        headers=auth(),
        json={"name": "Research", "description": "Project description"},
    )
    assert project_response.status_code == 201
    project = project_response.json()

    conversation_response = client.post(
        "/v1/conversations",
        headers=auth(),
        json={"title": "First conversation", "project_id": project["id"]},
    )
    assert conversation_response.status_code == 201
    conversation = conversation_response.json()
    root_id = conversation["root_branch_id"]

    listed_projects = client.get("/v1/projects", headers=auth())
    assert listed_projects.json()["items"][0]["id"] == project["id"]

    listed_conversations = client.get(
        "/v1/conversations?project_id=" + project["id"], headers=auth()
    )
    assert listed_conversations.json()["items"][0]["id"] == conversation["id"]

    first = client.post(
        f"/v1/branches/{root_id}/messages",
        headers=auth(),
        json={"role": "user", "participant": "user", "content": "Start here"},
    )
    assert first.status_code == 201

    fork = client.post(
        "/v1/branches",
        headers=auth(),
        json={
            "parent_branch_id": root_id,
            "fork_message_id": first.json()["id"],
            "name": "Alternative",
        },
    )
    assert fork.status_code == 201
    child_id = fork.json()["id"]

    child_message = client.post(
        f"/v1/branches/{child_id}/messages",
        headers=auth(),
        json={"role": "user", "participant": "user", "content": "Different path"},
    )
    assert child_message.status_code == 201

    history = client.get(
        f"/v1/branches/{child_id}/messages", headers=auth()
    )
    assert [item["content"] for item in history.json()["items"]] == [
        "Start here", "Different path"
    ]

    branches = client.get(
        f"/v1/conversations/{conversation['id']}/branches", headers=auth()
    )
    assert len(branches.json()["items"]) == 2


def test_api_rejects_invisible_fork_target_and_missing_branch(tmp_path):
    client = client_for(tmp_path)
    conversation = client.post(
        "/v1/conversations", headers=auth(), json={"title": "Conversation"}
    ).json()
    root_id = conversation["root_branch_id"]

    invalid = client.post(
        "/v1/branches",
        headers=auth(),
        json={
            "parent_branch_id": root_id,
            "fork_message_id": "not-visible",
            "name": "Invalid",
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_fork"

    missing = client.get("/v1/branches/not-a-branch/messages", headers=auth())
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_all_m1_routes_require_authentication(tmp_path):
    client = client_for(tmp_path)
    assert client.get("/v1/projects").status_code == 401
    assert client.post("/v1/projects", json={"name": "No auth"}).status_code == 401
    assert client.get("/v1/conversations").status_code == 401
