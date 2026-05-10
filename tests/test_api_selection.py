from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from quant_backtest.api.app import create_app
from quant_backtest.api.jobs import JobRegistry
from quant_backtest.data.cache import ParquetCache
from tests.conftest import make_bars


def test_job_registry_lifecycle():
    registry = JobRegistry(ttl_seconds=60)
    job_id = registry.create_job()
    state = registry.get(job_id)
    assert state.status == "pending"

    registry.update(job_id, status="running", stage="load_panel", progress=0.1, message="...")
    assert registry.get(job_id).stage == "load_panel"

    registry.complete(job_id, result={"candidates": []})
    final = registry.get(job_id)
    assert final.status == "done"
    assert final.result == {"candidates": []}


def test_job_registry_records_failure():
    registry = JobRegistry(ttl_seconds=60)
    job_id = registry.create_job()
    registry.fail(job_id, error="boom")
    state = registry.get(job_id)
    assert state.status == "failed"
    assert state.error == "boom"


def test_job_registry_purges_expired():
    registry = JobRegistry(ttl_seconds=0)
    job_id = registry.create_job()
    registry.complete(job_id, result={})
    time.sleep(0.01)
    registry.purge_expired()
    with pytest.raises(KeyError):
        registry.get(job_id)


@pytest.fixture()
def client_with_cache(tmp_path) -> TestClient:
    cache = ParquetCache(tmp_path / "cache")
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=80, start="2024-01-02"))
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    return TestClient(app)


def test_factors_listing(client_with_cache):
    response = client_with_cache.get("/api/selection/factors")
    assert response.status_code == 200
    keys = {f["key"] for f in response.json()["data"]}
    assert {"ma_breakout", "rsi_momentum", "macd_golden_cross"} <= keys


def test_defaults_listing(client_with_cache):
    response = client_with_cache.get("/api/selection/defaults")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["min_score"] == 2
    assert body["top_n"] == 20


def test_selection_job_lifecycle(client_with_cache):
    response = client_with_cache.post(
        "/api/selection/jobs",
        json={"as_of_date": None, "config": {"min_score": 0, "top_n": 5}, "symbol_universe": None},
    )
    assert response.status_code == 200
    job_id = response.json()["data"]["job_id"]

    state = None
    for _ in range(50):
        body = client_with_cache.get(f"/api/selection/jobs/{job_id}").json()["data"]
        if body["status"] == "done":
            state = body
            break
        if body["status"] == "failed":
            pytest.fail(f"job failed: {body['error']}")
        time.sleep(0.1)
    assert state is not None, "job did not complete in time"
    assert "candidates" in state["result"]
    assert "summary" in state["result"]


def test_selection_job_stream(client_with_cache):
    # Wait for job to finish via polling first so the SSE stream definitely
    # carries a "done" event without racing the test's read deadline.
    submit = client_with_cache.post(
        "/api/selection/jobs",
        json={"as_of_date": None, "config": {"min_score": 0, "top_n": 5}, "symbol_universe": None},
    )
    job_id = submit.json()["data"]["job_id"]
    for _ in range(50):
        body = client_with_cache.get(f"/api/selection/jobs/{job_id}").json()["data"]
        if body["status"] == "done":
            break
        time.sleep(0.1)
    else:
        pytest.fail("job did not reach done before stream test")

    saw_done = False
    saw_progress = False
    with client_with_cache.stream("GET", f"/api/selection/jobs/{job_id}/stream") as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event: progress"):
                saw_progress = True
            if line.startswith("event: done"):
                saw_done = True
                break
    assert saw_done, "never saw done event"


def test_unknown_job_returns_404(client_with_cache):
    response = client_with_cache.get("/api/selection/jobs/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.json()
