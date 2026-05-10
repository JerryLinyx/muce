"""Reports router — read-only browsing of sweep / validate runs."""

from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException

from quant_backtest.api.deps import ReportsDirDep
from quant_backtest.services import reports_service

router = APIRouter()


@router.get("")
def list_reports(
    reports_dir: ReportsDirDep,
    kind: str | None = None,
    since: date | None = None,
    limit: int | None = None,
) -> dict:
    items = reports_service.list_reports(reports_dir, kind=kind, since=since, limit=limit)
    return {"data": [m.to_dict() for m in items], "meta": {"count": len(items)}}


@router.get("/{run_id}")
def get_report(run_id: str, reports_dir: ReportsDirDep) -> dict:
    try:
        manifest = reports_service.load_report(reports_dir, run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"report not found: {run_id}")
    return {"data": manifest.to_dict(), "meta": {}}


@router.get("/{run_id}/equity")
def get_equity(run_id: str, reports_dir: ReportsDirDep) -> dict:
    return _artifact_response(reports_dir, run_id, "equity")


@router.get("/{run_id}/trades")
def get_trades(run_id: str, reports_dir: ReportsDirDep) -> dict:
    return _artifact_response(reports_dir, run_id, "trades")


@router.get("/{run_id}/sweep")
def get_sweep(run_id: str, reports_dir: ReportsDirDep) -> dict:
    return _artifact_response(reports_dir, run_id, "results")


def _artifact_response(reports_dir, run_id: str, name: str) -> dict:
    try:
        df = reports_service.load_artifact(reports_dir, run_id, name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"artifact not found: {run_id}/{name}")
    rows: list[dict] = []
    for record in df.to_dict(orient="records"):
        for key, value in list(record.items()):
            if isinstance(value, pd.Timestamp):
                record[key] = value.strftime("%Y-%m-%d")
        rows.append(record)
    return {"data": {"name": name, "rows": rows}, "meta": {"rows": len(rows)}}
