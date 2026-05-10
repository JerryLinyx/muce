from __future__ import annotations

from fastapi.testclient import TestClient

from quant_backtest.api.app import create_app


def test_health_returns_ok(tmp_path):
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"


def test_404_returns_rfc7807_envelope(tmp_path):
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    client = TestClient(app)
    response = client.get("/api/no-such-route")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]


def test_version_returns_payload(tmp_path):
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    client = TestClient(app)
    response = client.get("/api/version")
    assert response.status_code == 200
    body = response.json()["data"]
    assert "version" in body
    assert body["provider"] == "baostock"


def test_cors_allows_default_localhost_origins(tmp_path):
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    client = TestClient(app)
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_allows_vite_default_port(tmp_path):
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    client = TestClient(app)
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_blocks_unlisted_origin(tmp_path):
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    client = TestClient(app)
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # CORS middleware doesn't echo the disallowed origin back.
    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"


def test_cors_origins_overridable_by_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MUCE_API_CORS_ORIGINS", "http://example.com,http://other.test")
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    client = TestClient(app)
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://example.com"
    # Default localhost origins are no longer allowed in this configuration
    response2 = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response2.headers.get("access-control-allow-origin") != "http://localhost:3000"
