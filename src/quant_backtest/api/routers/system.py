"""Health and version endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from quant_backtest.api.deps import CacheDep, ReportsDirDep

router = APIRouter()


@router.get("/health")
def health(cache: CacheDep, reports_dir: ReportsDirDep) -> dict:
    return {
        "data": {
            "status": "ok",
            "cache_root_exists": cache.root.exists(),
            "reports_dir_exists": reports_dir.exists(),
        },
        "meta": {},
    }


@router.get("/version")
def version() -> dict:
    from importlib.metadata import version as _version

    try:
        v = _version("muce")
    except Exception:
        v = "0.0.0"
    return {"data": {"version": v, "provider": "baostock"}, "meta": {}}
