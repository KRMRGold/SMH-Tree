from fastapi.testclient import TestClient
from cogplat.config import Settings
from cogplat.main import create_app

def make_client(tmp_path):
    app = create_app(Settings(api_token="memory-token", data_dir=tmp_path))
    return TestClient(app)

def auth():
    return {"Authorization": "Bearer memory-token"}

def test_memory_api_crud_search_and_authentication(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/v1/memory").status_code == 401
    created = client.post(
        "/v1/memory", headers=auth(),
        json={"scope": "global", "kind": "preference", "content": "Prefer quiet dark rooms", "importance": 5},
    )
    assert created.status_code == 201
    item = created.json()
    assert item["schema_version"] == 1
    assert item["state"] == "active"
    found = client.get("/v1/memory?q=quiet%20dark", headers=auth())
    assert [entry["id"] for entry in found.json()["items"]] == [item["id"]]
    updated = client.patch(f"/v1/memory/{item['id']}", headers=auth(), json={"state": "outdated"})
    assert updated.status_code == 200
    assert updated.json()["state"] == "outdated"
    assert client.get("/v1/memory", headers=auth()).json()["items"] == []
    all_items = client.get("/v1/memory?state=all", headers=auth())
    assert all_items.json()["items"][0]["content"] == "Prefer quiet dark rooms"

def test_memory_api_validates_scope_and_context(tmp_path):
    client = make_client(tmp_path)
    invalid = client.post(
        "/v1/memory", headers=auth(),
        json={"scope": "global", "scope_id": "not-allowed", "kind": "fact", "content": "Bad scope"},
    )
    assert invalid.status_code == 422
    project = client.post("/v1/projects", headers=auth(), json={"name": "Project"}).json()
    conversation = client.post(
        "/v1/conversations", headers=auth(),
        json={"title": "Conversation", "project_id": project["id"]},
    ).json()
    valid = client.post(
        "/v1/memory", headers=auth(),
        json={"scope": "branch", "scope_id": conversation["root_branch_id"], "kind": "decision", "content": "Branch decision"},
    )
    assert valid.status_code == 201
    wrong_context = client.get(
        f"/v1/memory?branch_id={conversation['root_branch_id']}&project_id=wrong", headers=auth()
    )
    assert wrong_context.status_code == 422

def test_memory_item_detail_obeys_branch_scope_eligibility(tmp_path):
    client = make_client(tmp_path)
    project = client.post("/v1/projects", headers=auth(), json={"name": "Project"}).json()
    conversation = client.post(
        "/v1/conversations", headers=auth(), json={"title": "Conversation", "project_id": project["id"]}
    ).json()
    root = conversation["root_branch_id"]
    message = client.post(
        f"/v1/branches/{root}/messages", headers=auth(),
        json={"role": "user", "participant": "user", "content": "Fork point"},
    ).json()
    fork = client.post(
        "/v1/branches", headers=auth(),
        json={"parent_branch_id": root, "fork_message_id": message["id"], "name": "Child"},
    ).json()
    root_memory = client.post(
        "/v1/memory", headers=auth(),
        json={"scope": "branch", "scope_id": root, "kind": "fact", "content": "Root memory"},
    ).json()
    child_memory = client.post(
        "/v1/memory", headers=auth(),
        json={"scope": "branch", "scope_id": fork["id"], "kind": "fact", "content": "Child memory"},
    ).json()
    inherited = client.get(f"/v1/memory/{root_memory['id']}?branch_id={fork['id']}", headers=auth())
    own = client.get(f"/v1/memory/{child_memory['id']}?branch_id={fork['id']}", headers=auth())
    assert inherited.status_code == 200
    assert own.status_code == 200

def test_memory_api_supersede_requires_replacement_in_same_scope(tmp_path):
    client = make_client(tmp_path)
    old = client.post(
        "/v1/memory", headers=auth(),
        json={"scope": "global", "kind": "fact", "content": "Old preference"},
    ).json()
    new = client.post(
        "/v1/memory", headers=auth(),
        json={"scope": "global", "kind": "fact", "content": "New preference"},
    ).json()
    response = client.patch(
        f"/v1/memory/{old['id']}", headers=auth(),
        json={"state": "superseded", "superseded_by": new["id"]},
    )
    assert response.status_code == 200
    assert response.json()["superseded_by"] == new["id"]
