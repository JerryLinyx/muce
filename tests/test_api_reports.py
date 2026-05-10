from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from quant_backtest.api.app import create_app
from quant_backtest.reports.store import write_report


@pytest.fixture()
def client_with_reports(tmp_path) -> TestClient:
    reports_dir = tmp_path / "reports"
    write_report(
        kind="sweep",
        config={"strategy": "demo", "fast": 5},
        manifest_extra={
            "elapsed_seconds": 1.2,
            "data_range": {"start": "2026-05-08", "end": "2026-05-09"},
            "symbols": ["000001.SZ"],
            "strategy": "demo",
            "grid_size": 2,
            "rank_by": "total_return",
            "top_combos": [{"combo_id": 1, "total_return": 0.1}],
        },
        artifacts={
            "results": pd.DataFrame({"combo_id": [1, 2], "total_return": [0.1, 0.2]})
        },
        base_dir=reports_dir,
    )
    write_report(
        kind="validate",
        config={"strategy": "validate-demo", "fast": 5, "slow": 20},
        manifest_extra={
            "elapsed_seconds": 3.4,
            "data_range": {"start": "2026-05-08", "end": "2026-05-09"},
            "symbols": ["000001.SZ"],
            "strategy": "validate-demo",
            "signal_adjust": "qfq",
            "execution_adjust": "raw",
            "summary_metrics": {
                "total_return": 0.05,
                "sharpe": 0.8,
                "max_drawdown": -0.02,
                "trades": 3,
            },
        },
        artifacts={
            "equity": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2026-05-08", "2026-05-09"]),
                    "equity": [1.0, 1.05],
                }
            ),
            "trades": pd.DataFrame(
                {"trade_id": [1], "symbol": ["000001.SZ"], "pnl": [0.05]}
            ),
        },
        base_dir=reports_dir,
    )
    app = create_app(cache_root=tmp_path / "cache", reports_dir=reports_dir)
    return TestClient(app)


def test_list_reports(client_with_reports):
    response = client_with_reports.get("/api/reports")
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    kinds = {item["kind"] for item in items}
    assert kinds == {"sweep", "validate"}


def test_list_reports_filtered_by_kind(client_with_reports):
    response = client_with_reports.get("/api/reports?kind=sweep")
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["kind"] == "sweep"


def test_load_report_detail(client_with_reports):
    listing = client_with_reports.get("/api/reports?kind=validate").json()["data"]
    run_id = listing[0]["run_id"]
    detail = client_with_reports.get(f"/api/reports/{run_id}")
    assert detail.status_code == 200
    body = detail.json()["data"]
    assert body["run_id"] == run_id
    assert body["summary_metrics"]["total_return"] == 0.05


def test_load_validate_artifacts(client_with_reports):
    listing = client_with_reports.get("/api/reports?kind=validate").json()["data"]
    run_id = listing[0]["run_id"]
    equity = client_with_reports.get(f"/api/reports/{run_id}/equity").json()["data"]
    assert len(equity["rows"]) == 2
    trades = client_with_reports.get(f"/api/reports/{run_id}/trades").json()["data"]
    assert len(trades["rows"]) == 1


def test_load_sweep_artifact(client_with_reports):
    listing = client_with_reports.get("/api/reports?kind=sweep").json()["data"]
    run_id = listing[0]["run_id"]
    sweep = client_with_reports.get(f"/api/reports/{run_id}/sweep").json()["data"]
    assert len(sweep["rows"]) == 2


def test_404_for_unknown_run_id(client_with_reports):
    response = client_with_reports.get(
        "/api/reports/sweep-19990101-000000-000000"
    )
    assert response.status_code == 404
    assert "error" in response.json()
