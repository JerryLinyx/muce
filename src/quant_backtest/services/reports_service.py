"""Service-layer wrapper for the reports/ on-disk store."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from quant_backtest.reports import store
from quant_backtest.reports.schema import ReportManifest


def list_reports(
    base_dir: Path,
    *,
    kind: str | None = None,
    since: date | None = None,
    limit: int | None = None,
) -> list[ReportManifest]:
    return store.list_reports(base_dir, kind=kind, since=since, limit=limit)


def load_report(base_dir: Path, run_id: str) -> ReportManifest:
    return store.load_report(base_dir, run_id)


def load_artifact(base_dir: Path, run_id: str, name: str) -> pd.DataFrame:
    return store.load_artifact(base_dir, run_id, name)
