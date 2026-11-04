from fastapi.testclient import TestClient

from tests.conftest import make_token


def test_health_does_not_require_auth(client: TestClient) -> None:
    client.headers.pop("Authorization", None)
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_route_rejects_missing_token(client: TestClient) -> None:
    client.headers.pop("Authorization", None)
    response = client.get("/api/v1/system/diagnostics")
    assert response.status_code == 401


def test_protected_route_rejects_invalid_token(client: TestClient) -> None:
    client.headers.update({"Authorization": "Bearer not-a-real-token"})
    response = client.get("/api/v1/system/diagnostics")
    assert response.status_code == 401


def test_protected_route_rejects_token_signed_with_wrong_secret(client: TestClient) -> None:
    client.headers.update({"Authorization": f"Bearer {make_token(secret='some-other-secret')}"})
    response = client.get("/api/v1/system/diagnostics")
    assert response.status_code == 401


def test_protected_route_accepts_bearer_header(client: TestClient) -> None:
    response = client.get("/api/v1/system/diagnostics")
    assert response.status_code == 200


def test_protected_route_accepts_query_param_token(client: TestClient) -> None:
    token = client.headers["Authorization"].removeprefix("Bearer ")
    client.headers.pop("Authorization", None)
    response = client.get(f"/api/v1/system/diagnostics?token={token}")
    assert response.status_code == 200
