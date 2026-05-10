"""FastAPI application factory + console-script entrypoint."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from quant_backtest.api.errors import install_error_handlers
from quant_backtest.api.jobs import JobRegistry
from quant_backtest.api.routers import data as data_router
from quant_backtest.api.routers import reports as reports_router
from quant_backtest.api.routers import selection as selection_router
from quant_backtest.api.routers import system as system_router
from quant_backtest.data.cache import ParquetCache


_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def create_app(
    *,
    cache_root: Path | str | None = None,
    reports_dir: Path | str | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    cache_root_path = Path(
        cache_root or os.environ.get("MUCE_CACHE_ROOT", "data/cache/a_share/daily")
    )
    reports_dir_path = Path(reports_dir or os.environ.get("MUCE_REPORTS_DIR", "reports"))

    if cors_origins is None:
        env_origins = os.environ.get("MUCE_API_CORS_ORIGINS", "")
        cors_origins = (
            [origin.strip() for origin in env_origins.split(",") if origin.strip()]
            or list(_DEFAULT_CORS_ORIGINS)
        )

    app = FastAPI(title="Muce API", version="0.1.0")
    app.state.cache = ParquetCache(cache_root_path)
    app.state.reports_dir = reports_dir_path
    app.state.job_registry = JobRegistry(ttl_seconds=3600)
    app.state.cors_origins = list(cors_origins)

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

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
