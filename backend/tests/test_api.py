from fastapi.testclient import TestClient

from cogplat.config import Settings
from cogplat.main import create_app


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
        "version": "0.2.0",
        "schema_version": 1,
        "capabilities": {
            "sqlite": True,
            "sqlite_fts5": True,
            "branching": True,
            "chat": True,
            "streaming": True,
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
