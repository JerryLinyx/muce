"""Data router — symbol search, K-line, cache coverage."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from quant_backtest.api.deps import CacheDep
from quant_backtest.services import data_service

router = APIRouter()


@router.get("/symbols")
def list_symbols(
    cache: CacheDep,
    q: str | None = None,
    market: str | None = None,
    adjust: str = "qfq",
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    rows = data_service.list_symbols(
        cache, adjust=adjust, query=q, market=market, limit=limit, offset=offset
    )
    payload = [
        {
            "symbol": row.symbol,
            "market": row.market,
            "last_cached_date": row.last_cached_date.isoformat() if row.last_cached_date else None,
        }
        for row in rows
    ]
    return {"data": payload, "meta": {"count": len(payload)}}


@router.get("/symbols/{symbol}")
def symbol_info(symbol: str, cache: CacheDep, adjust: str = "qfq") -> dict:
    info = data_service.symbol_info(cache, symbol, adjust=adjust)
    if info.last_cached_date is None:
        raise HTTPException(status_code=404, detail=f"symbol not in cache: {symbol}")
    return {
        "data": {
            "symbol": info.symbol,
            "market": info.market,
            "last_cached_date": info.last_cached_date.isoformat(),
        },
        "meta": {},
    }


@router.get("/bars/{symbol}")
def bars(
    symbol: str,
    cache: CacheDep,
    adjust: str = "qfq",
    start: date | None = None,
    end: date | None = None,
    indicators: str = "",
) -> dict:
    indicator_tuple = tuple(filter(None, indicators.split(",")))
    try:
        result = data_service.load_bars_with_indicators(
            cache, symbol, adjust=adjust, start=start, end=end, indicators=indicator_tuple
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "data": {
            "symbol": result.symbol,
            "adjust": result.adjust,
            "indicators_requested": list(result.indicators_requested),
            "rows": result.rows,
        },
        "meta": {"rows": len(result.rows)},
    }


@router.get("/cache/coverage")
def cache_coverage(cache: CacheDep, adjust: str = "qfq") -> dict:
    entries = data_service.cache_coverage(cache, adjust=adjust)
    payload = [
        {
            "symbol": entry.symbol,
            "rows": entry.rows,
            "first_date": entry.first_date.isoformat() if entry.first_date else None,
            "last_date": entry.last_date.isoformat() if entry.last_date else None,
        }
        for entry in entries
    ]
    return {"data": payload, "meta": {"count": len(payload)}}
