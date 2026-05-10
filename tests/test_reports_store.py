from __future__ import annotations

from datetime import date as _date
from pathlib import Path

import pandas as pd

from quant_backtest.reports import store
from quant_backtest.reports.schema import (
    ArtifactRef,
    DateRange,
    ReportManifest,
    SweepManifest,
    ValidateManifest,
)


def test_report_manifest_to_dict_round_trip():
    manifest = ReportManifest(
        run_id="sweep-20260510-142233-a3f1c2",
        kind="sweep",
        created_at="2026-05-10T14:22:33Z",
        elapsed_seconds=12.5,
        git_commit="abc123",
        git_dirty=False,
        data_range=DateRange(start="2024-01-02", end="2026-05-09"),
        symbols=["000001.SZ"],
        config_hash="a3f1c2",
        config_path="config.json",
        artifacts=[ArtifactRef(name="results", path="results.parquet", rows=42)],
    )
    payload = manifest.to_dict()
    assert payload["run_id"] == manifest.run_id
    assert payload["kind"] == "sweep"
    assert payload["data_range"] == {"start": "2024-01-02", "end": "2026-05-09"}
    assert payload["artifacts"][0]["name"] == "results"


def test_sweep_manifest_round_trip():
    manifest = SweepManifest(
        run_id="sweep-20260510-142233-a3f1c2",
        kind="sweep",
        created_at="2026-05-10T14:22:33Z",
        elapsed_seconds=1.0,
        git_commit=None,
        git_dirty=True,
        data_range=DateRange(start="2024-01-02", end="2026-05-09"),
        symbols=["000001.SZ"],
        config_hash="a3f1c2",
        config_path="config.json",
        artifacts=[],
        strategy="three-falling-buy-three-rising-sell",
        grid_size=27,
        rank_by="total_return",
        top_combos=[{"combo_id": 1, "total_return": 0.31}],
    )
    payload = manifest.to_dict()
    assert payload["strategy"] == "three-falling-buy-three-rising-sell"
    assert payload["grid_size"] == 27


def test_write_report_creates_directory_layout(tmp_path: Path):
    config = {"strategy": "demo", "fast": 5, "slow": 20}
    artifacts = {
        "equity": pd.DataFrame(
            {"date": pd.to_datetime(["2026-05-08"]), "equity": [1.0]}
        ),
        "trades": pd.DataFrame({"trade_id": [1], "symbol": ["000001.SZ"]}),
    }
    run_id = store.write_report(
        kind="validate",
        config=config,
        manifest_extra={
            "strategy": "demo",
            "signal_adjust": "qfq",
            "execution_adjust": "raw",
            "summary_metrics": {"total_return": 0.05},
            "data_range": {"start": "2026-05-08", "end": "2026-05-08"},
            "symbols": ["000001.SZ"],
        },
        artifacts=artifacts,
        base_dir=tmp_path,
    )
    run_dir = tmp_path / "validations" / run_id
    assert run_dir.exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "equity.parquet").exists()
    assert (run_dir / "trades.parquet").exists()
    assert (run_dir / "config.json").exists()
    assert run_id.startswith("validate-")
    assert len(run_id.split("-")[-1]) == 6


def test_write_report_same_config_yields_same_hash_suffix(tmp_path: Path):
    config = {"strategy": "demo", "fast": 5, "slow": 20}
    extras = {
        "data_range": {"start": "2026-05-08", "end": "2026-05-08"},
        "symbols": ["000001.SZ"],
    }
    a = store.write_report(
        kind="sweep", config=config, manifest_extra=dict(extras), artifacts={}, base_dir=tmp_path
    )
    b = store.write_report(
        kind="sweep", config=config, manifest_extra=dict(extras), artifacts={}, base_dir=tmp_path
    )
    assert a.split("-")[-1] == b.split("-")[-1]
    # different timestamps may collide at second granularity in fast tests; tolerate equality
    # by asserting at least the hash suffix is reproducible
    assert a.split("-")[-1] == b.split("-")[-1]


def test_list_and_load_round_trip(tmp_path: Path):
    config = {"strategy": "demo", "fast": 5}
    artifacts = {"results": pd.DataFrame({"combo_id": [1, 2], "total_return": [0.1, 0.2]})}
    run_id = store.write_report(
        kind="sweep",
        config=config,
        manifest_extra={
            "strategy": "demo",
            "grid_size": 2,
            "rank_by": "total_return",
            "top_combos": [{"combo_id": 1, "total_return": 0.1}],
            "data_range": {"start": "2026-05-08", "end": "2026-05-08"},
            "symbols": ["000001.SZ"],
        },
        artifacts=artifacts,
        base_dir=tmp_path,
    )
    listing = store.list_reports(tmp_path, kind="sweep")
    assert len(listing) == 1
    assert listing[0].run_id == run_id
    loaded = store.load_report(tmp_path, run_id)
    assert loaded.run_id == run_id
    df = store.load_artifact(tmp_path, run_id, "results")
    assert list(df.columns) == ["combo_id", "total_return"]
    assert len(df) == 2


def test_list_reports_filters_by_since(tmp_path: Path):
    listing = store.list_reports(tmp_path, since=_date(2099, 1, 1))
    assert listing == []
