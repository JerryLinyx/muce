"""Service-layer helpers for browsing the on-disk daily bar cache."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import SOURCE_BAOSTOCK
from quant_backtest.features.indicators import (
    TechnicalIndicatorConfig,
    add_technical_indicators,
)


@dataclass(frozen=True)
class SymbolRow:
    symbol: str
    market: str
    last_cached_date: date | None


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str
    market: str
    last_cached_date: date | None


@dataclass(frozen=True)
class BarsResult:
    symbol: str
    adjust: str
    indicators_requested: tuple[str, ...]
    rows: list[dict]


@dataclass(frozen=True)
class CoverageEntry:
    symbol: str
    rows: int
    first_date: date | None
    last_date: date | None


def list_symbols(
    cache: ParquetCache,
    *,
    adjust: str = "qfq",
    source: str = SOURCE_BAOSTOCK,
    query: str | None = None,
    market: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[SymbolRow]:
    symbols = cache.available_symbols(source=source, adjust=adjust)
    rows: list[SymbolRow] = []
    for symbol in symbols:
        market_code = symbol.split(".")[-1]
        if market and market_code != market:
            continue
        if query and not symbol.startswith(query):
            continue
        last_ts = cache.last_date(source=source, adjust=adjust, symbol=symbol)
        last = last_ts.date() if isinstance(last_ts, pd.Timestamp) else None
        rows.append(SymbolRow(symbol=symbol, market=market_code, last_cached_date=last))
    if offset:
        rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]
    return rows


def symbol_info(
    cache: ParquetCache,
    symbol: str,
    *,
    adjust: str = "qfq",
    source: str = SOURCE_BAOSTOCK,
) -> SymbolInfo:
    market = symbol.split(".")[-1]
    last_ts = cache.last_date(source=source, adjust=adjust, symbol=symbol)
    last = last_ts.date() if isinstance(last_ts, pd.Timestamp) else None
    return SymbolInfo(symbol=symbol, market=market, last_cached_date=last)


def load_bars_with_indicators(
    cache: ParquetCache,
    symbol: str,
    *,
    adjust: str = "qfq",
    source: str = SOURCE_BAOSTOCK,
    start: date | str | None = None,
    end: date | str | None = None,
    indicators: tuple[str, ...] = (),
) -> BarsResult:
    df = cache.read_symbol(
        source=source,
        adjust=adjust,
        symbol=symbol,
        start=str(start) if start is not None else None,
        end=str(end) if end is not None else None,
    )
    if indicators:
        ma_windows = tuple(
            sorted({int(name.split("_", 1)[1]) for name in indicators if name.startswith("ma_")})
        )
        rsi_windows = [int(name.split("_", 1)[1]) for name in indicators if name.startswith("rsi_")]
        kwargs: dict = {}
        if ma_windows:
            kwargs["ma_windows"] = ma_windows
        if rsi_windows:
            kwargs["rsi_window"] = rsi_windows[0]
        config = TechnicalIndicatorConfig(**kwargs) if kwargs else TechnicalIndicatorConfig()
        df = add_technical_indicators(df, config=config)

    keep_cols = ["date", "open", "high", "low", "close", "volume", "amount"]
    keep_cols.extend(name for name in indicators if name in df.columns)

    rows: list[dict] = []
    for record in df[keep_cols].to_dict(orient="records"):
        record["date"] = pd.Timestamp(record["date"]).strftime("%Y-%m-%d")
        rows.append(record)
    return BarsResult(
        symbol=symbol,
        adjust=adjust,
        indicators_requested=tuple(indicators),
        rows=rows,
    )


def cache_coverage(
    cache: ParquetCache,
    *,
    adjust: str = "qfq",
    source: str = SOURCE_BAOSTOCK,
) -> list[CoverageEntry]:
    entries: list[CoverageEntry] = []
    for symbol in cache.available_symbols(source=source, adjust=adjust):
        try:
            df = cache.read_symbol(source=source, adjust=adjust, symbol=symbol)
        except FileNotFoundError:
            continue
        if df.empty:
            entries.append(CoverageEntry(symbol=symbol, rows=0, first_date=None, last_date=None))
            continue
        first_ts = df["date"].min()
        last_ts = df["date"].max()
        entries.append(
            CoverageEntry(
                symbol=symbol,
                rows=int(len(df)),
                first_date=first_ts.date() if isinstance(first_ts, pd.Timestamp) else None,
                last_date=last_ts.date() if isinstance(last_ts, pd.Timestamp) else None,
            )
        )
    return entries
