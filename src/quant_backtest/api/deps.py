"""FastAPI dependency injection for cache and reports directory."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

from quant_backtest.data.cache import ParquetCache


def get_cache(request: Request) -> ParquetCache:
    return request.app.state.cache


def get_reports_dir(request: Request) -> Path:
    return request.app.state.reports_dir


CacheDep = Annotated[ParquetCache, Depends(get_cache)]
ReportsDirDep = Annotated[Path, Depends(get_reports_dir)]
