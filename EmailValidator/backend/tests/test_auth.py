import sys
import types
from unittest.mock import patch

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


def _fake_qapplication_module(main_window: object | None) -> types.ModuleType:
    """A stand-in for PySide6.QtWidgets, since this backend's own venv -
    unlike the real desktop app's - has no reason to depend on PySide6.
    Only /api/v1/session/local ever touches it, and only when actually
    bundled into the desktop app."""
    module = types.ModuleType("PySide6.QtWidgets")

    class FakeQApplication:
        @staticmethod
        def instance():
            return types.SimpleNamespace(main_window=main_window) if main_window is not None else None

    module.QApplication = FakeQApplication
    return module


def test_local_session_404s_when_not_bundled_in_the_desktop_app(client: TestClient) -> None:
    # The real condition for this backend's own test/dev venv: no PySide6.
    client.headers.pop("Authorization", None)
    response = client.get("/api/v1/session/local")
    assert response.status_code == 404


def test_local_session_rejects_when_desktop_app_not_signed_in(client: TestClient) -> None:
    client.headers.pop("Authorization", None)
    main_window = types.SimpleNamespace(state=types.SimpleNamespace(logged_in=False, auth_token=""))
    with patch.dict(sys.modules, {"PySide6.QtWidgets": _fake_qapplication_module(main_window)}):
        response = client.get("/api/v1/session/local")
    assert response.status_code == 401


def test_local_session_hands_out_the_desktop_apps_own_token_when_signed_in(client: TestClient) -> None:
    client.headers.pop("Authorization", None)
    desktop_token = make_token()
    main_window = types.SimpleNamespace(state=types.SimpleNamespace(logged_in=True, auth_token=desktop_token))
    with patch.dict(sys.modules, {"PySide6.QtWidgets": _fake_qapplication_module(main_window)}):
        response = client.get("/api/v1/session/local")
    assert response.status_code == 200
    assert response.json()["token"] == desktop_token
