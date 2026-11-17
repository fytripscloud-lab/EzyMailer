import sys
import types
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.core.auth as auth_module
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


def test_a_token_the_remote_ezymailer_backend_confirms_is_accepted(client: TestClient) -> None:
    # Stands in for a real production token: signed with the live server's
    # own secret, which this process never holds, so local verification
    # fails and it has to fall through to asking that backend directly.
    client.headers.update({"Authorization": "Bearer production.signed.token"})
    with patch.object(auth_module, "_verify_with_ezymailer_backend", AsyncMock(return_value=True)):
        response = client.get("/api/v1/system/diagnostics")
    assert response.status_code == 200


def test_remote_verification_result_is_cached_within_the_ttl(client: TestClient) -> None:
    client.headers.update({"Authorization": "Bearer production.signed.token"})
    mock_verify = AsyncMock(return_value=True)
    with patch.object(auth_module, "_verify_with_ezymailer_backend", mock_verify):
        first = client.get("/api/v1/system/diagnostics")
        second = client.get("/api/v1/system/diagnostics")
    assert first.status_code == 200
    assert second.status_code == 200
    assert mock_verify.call_count == 1


def test_rejected_when_the_remote_ezymailer_backend_says_the_token_is_invalid(client: TestClient) -> None:
    client.headers.update({"Authorization": "Bearer production.signed.token"})
    with patch.object(auth_module, "_verify_with_ezymailer_backend", AsyncMock(return_value=False)):
        response = client.get("/api/v1/system/diagnostics")
    assert response.status_code == 401


def test_remote_verification_fails_closed_when_the_backend_is_unreachable(client: TestClient) -> None:
    # EZYM_MAILER_API_BASE_URL is pointed at a port nothing listens on in
    # tests (see conftest.test_settings) - this exercises that for real,
    # without mocking _verify_with_ezymailer_backend itself.
    client.headers.update({"Authorization": "Bearer production.signed.token"})
    response = client.get("/api/v1/system/diagnostics")
    assert response.status_code == 401


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
