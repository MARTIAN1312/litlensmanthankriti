from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_reports_providers(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["providers"] == {"groq": True, "gemini": False}
    assert body["env"] == "dev"


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "NOT_FOUND", "message": "Not Found"}}


def test_docs_disabled_in_prod(settings: Settings) -> None:
    prod = settings.model_copy(update={"env": "prod"})
    with TestClient(create_app(prod)) as c:
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404


def test_docs_enabled_in_dev(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200


def test_cors_allows_only_configured_origin(client: TestClient) -> None:
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_unhandled_error_hides_details(settings: Settings) -> None:
    app = create_app(settings)

    @app.get("/api/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "INTERNAL"
    assert "secret" not in r.text
