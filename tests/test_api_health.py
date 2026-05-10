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
