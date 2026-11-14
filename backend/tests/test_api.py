from fastapi.testclient import TestClient

from cogplat.config import Settings
from cogplat.db.connection import connect_db
from cogplat.main import create_app
from cogplat.repos import context_snapshots as snapshot_repo
from cogplat.repos import runs as run_repo


def make_client(tmp_path):
    app = create_app(Settings(api_token="test-token", data_dir=tmp_path))
    return TestClient(app)


def test_health_requires_a_valid_bearer_token(tmp_path):
    client = make_client(tmp_path)

    missing = client.get("/v1/health")
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "unauthorized"

    incorrect = client.get(
        "/v1/health", headers={"Authorization": "Bearer incorrect"}
    )
    assert incorrect.status_code == 401
    assert incorrect.json()["error"]["code"] == "unauthorized"

    response = client.get(
        "/v1/health", headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.8.1",
        "schema_version": 6,
        "capabilities": {
            "sqlite": True,
            "sqlite_fts5": True,
            "branching": True,
            "chat": True,
            "streaming": True,
            "memory": True,
            "epistemic": True,
            "workflows": True,
        },
    }


def test_openapi_endpoint_is_authenticated(tmp_path):
    client = make_client(tmp_path)

    assert client.get("/v1/openapi.json").status_code == 401
    response = client.get(
        "/v1/openapi.json", headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "SMH-Tree API"


def test_default_fastapi_docs_are_disabled(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_transmissions_endpoint_requires_authentication(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/v1/transmissions").status_code == 401
    response = client.get("/v1/transmissions", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_remote_memory_sharing_settings_are_authenticated_and_default_off(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/v1/settings").status_code == 401
    headers = {"Authorization": "Bearer test-token"}

    initial = client.get("/v1/settings", headers=headers)
    assert initial.status_code == 200
    assert initial.json() == {
        "share_global_memory_remote": False,
        "share_user_memory_remote": False,
    }

    updated = client.patch(
        "/v1/settings",
        headers=headers,
        json={"share_global_memory_remote": True},
    )
    assert updated.status_code == 200
    assert updated.json() == {
        "share_global_memory_remote": True,
        "share_user_memory_remote": False,
    }
    assert client.get("/v1/settings", headers=headers).json()["share_global_memory_remote"] is True


def test_remote_memory_sharing_settings_reject_unknown_or_non_boolean_values(tmp_path):
    client = make_client(tmp_path)
    headers = {"Authorization": "Bearer test-token"}
    assert client.patch(
        "/v1/settings", headers=headers, json={"unexpected": True}
    ).status_code == 422
    assert client.patch(
        "/v1/settings", headers=headers, json={"share_user_memory_remote": "yes"}
    ).status_code == 422


def test_latest_branch_run_returns_newest_snapshotted_chat_run(tmp_path):
    client = make_client(tmp_path)
    headers = {"Authorization": "Bearer test-token"}
    conversation = client.post(
        "/v1/conversations",
        headers=headers,
        json={"title": "Context history", "project_id": None},
    ).json()
    branch_id = conversation["root_branch_id"]

    endpoint = f"/v1/branches/{branch_id}/runs/latest"
    assert client.get(endpoint).status_code == 401
    assert client.get(endpoint, headers=headers).json() == {"run": None}
    assert client.get(
        "/v1/branches/missing/runs/latest", headers=headers
    ).status_code == 404

    connection = connect_db(tmp_path / "app.db")
    try:
        with connection:
            first = run_repo.create_run(
                connection, "chat_turn", conversation["id"], branch_id, False, {}
            )
            snapshot_repo.create_snapshot(
                connection, first["id"], "Test provider", {"messages": []}, 0
            )
            latest = run_repo.create_run(
                connection, "chat_turn", conversation["id"], branch_id, False, {}
            )
            snapshot_repo.create_snapshot(
                connection, latest["id"], "Test provider", {"messages": []}, 0
            )
    finally:
        connection.close()

    response = client.get(endpoint, headers=headers)
    assert response.status_code == 200
    assert response.json()["run"]["id"] == latest["id"]
