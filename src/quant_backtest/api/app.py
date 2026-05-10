"""FastAPI application factory + console-script entrypoint."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from quant_backtest.api.errors import install_error_handlers
from quant_backtest.api.jobs import JobRegistry
from quant_backtest.api.routers import data as data_router
from quant_backtest.api.routers import reports as reports_router
from quant_backtest.api.routers import selection as selection_router
from quant_backtest.api.routers import system as system_router
from quant_backtest.data.cache import ParquetCache


def create_app(
    *,
    cache_root: Path | str | None = None,
    reports_dir: Path | str | None = None,
) -> FastAPI:
    cache_root_path = Path(
        cache_root or os.environ.get("MUCE_CACHE_ROOT", "data/cache/a_share/daily")
    )
    reports_dir_path = Path(reports_dir or os.environ.get("MUCE_REPORTS_DIR", "reports"))

    app = FastAPI(title="Muce API", version="0.1.0")
    app.state.cache = ParquetCache(cache_root_path)
    app.state.reports_dir = reports_dir_path
    app.state.job_registry = JobRegistry(ttl_seconds=3600)

    install_error_handlers(app)
    app.include_router(system_router.router, prefix="/api")
    app.include_router(data_router.router, prefix="/api")
    app.include_router(reports_router.router, prefix="/api/reports")
    app.include_router(selection_router.router, prefix="/api/selection")
    return app


app = create_app()


def run() -> None:
    """Console-script entrypoint for `quant-api`."""
    import uvicorn

    uvicorn.run(
        "quant_backtest.api.app:app",
        host=os.environ.get("MUCE_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("MUCE_API_PORT", "8000")),
        reload=bool(os.environ.get("MUCE_API_RELOAD", "")),
    )
