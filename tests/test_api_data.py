from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from quant_backtest.api.app import create_app
from quant_backtest.data.cache import ParquetCache
from tests.conftest import make_bars


@pytest.fixture()
def client(tmp_path) -> TestClient:
    cache = ParquetCache(tmp_path / "cache")
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=3, start="2026-05-07"))
    cache.write(make_bars("600000.SH", adjust="qfq", rows=2, start="2026-05-08"))
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    return TestClient(app)


def test_list_symbols(client):
    response = client.get("/api/symbols")
    assert response.status_code == 200
    symbols = [s["symbol"] for s in response.json()["data"]]
    assert set(symbols) == {"000001.SZ", "600000.SH"}


def test_list_symbols_filter_by_market(client):
    response = client.get("/api/symbols?market=SZ")
    assert response.status_code == 200
    symbols = [s["symbol"] for s in response.json()["data"]]
    assert symbols == ["000001.SZ"]


def test_symbol_info(client):
    response = client.get("/api/symbols/000001.SZ")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["symbol"] == "000001.SZ"
    assert body["market"] == "SZ"
    assert body["last_cached_date"] is not None


def test_symbol_info_missing(client):
    response = client.get("/api/symbols/999999.SZ")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body


def test_bars(client):
    response = client.get("/api/bars/000001.SZ?adjust=qfq")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["symbol"] == "000001.SZ"
    assert len(body["rows"]) == 3


def test_cache_coverage(client):
    response = client.get("/api/cache/coverage")
    assert response.status_code == 200
    coverage = {entry["symbol"]: entry for entry in response.json()["data"]}
    assert coverage["000001.SZ"]["rows"] == 3
    assert coverage["600000.SH"]["rows"] == 2
