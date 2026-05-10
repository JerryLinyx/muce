from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import Adjust, SOURCE_BAOSTOCK

DEFAULT_VECTORBT_FIELDS = ["open", "high", "low", "close", "volume"]


def load_for_vectorbt(
    cache: ParquetCache,
    symbols: Iterable[str],
    *,
    fields: Iterable[str] = DEFAULT_VECTORBT_FIELDS,
    start: str | None = None,
    end: str | None = None,
    source: str = SOURCE_BAOSTOCK,
    adjust: Adjust = "qfq",
) -> dict[str, pd.DataFrame]:
    data = cache.read_many(source=source, adjust=adjust, symbols=list(symbols), start=start, end=end)
    if data.empty:
        return {field: pd.DataFrame() for field in fields}

    panels: dict[str, pd.DataFrame] = {}
    for field in fields:
        if field not in data.columns:
            raise KeyError(f"field {field!r} is not available in cached data")
        panel = data.pivot(index="date", columns="symbol", values=field).sort_index()
        panels[field] = panel
    return panels


def load_backtrader_frame(
    cache: ParquetCache,
    symbol: str,
    *,
    start: str | None = None,
    end: str | None = None,
    source: str = SOURCE_BAOSTOCK,
    price_mode: Adjust = "raw",
) -> pd.DataFrame:
    data = cache.read_symbol(source=source, adjust=price_mode, symbol=symbol, start=start, end=end)
    if data.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "openinterest"])

    frame = data.loc[:, ["date", "open", "high", "low", "close", "volume"]].copy()
    frame["openinterest"] = 0
    frame = frame.rename(columns={"date": "datetime"}).set_index("datetime")
    return frame.sort_index()


def load_backtrader_signal_execution_frame(
    cache: ParquetCache,
    symbol: str,
    *,
    start: str | None = None,
    end: str | None = None,
    source: str = SOURCE_BAOSTOCK,
    signal_adjust: Adjust = "qfq",
    execution_adjust: Adjust = "raw",
) -> pd.DataFrame:
    execution = cache.read_symbol(
        source=source,
        adjust=execution_adjust,
        symbol=symbol,
        start=start,
        end=end,
    )
    signal = cache.read_symbol(
        source=source,
        adjust=signal_adjust,
        symbol=symbol,
        start=start,
        end=end,
    )
    if execution.empty:
        return pd.DataFrame(
            columns=[
                "open",
                "high",
                "low",
                "close",
                "volume",
                "openinterest",
                "signal_open",
                "signal_high",
                "signal_low",
                "signal_close",
                "signal_volume",
            ]
        )

    raw = execution.loc[
        :,
        [
            "date",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "volume",
            "amount",
            "trade_status",
            "is_st",
        ],
    ].copy()
    sig = signal.loc[:, ["date", "symbol", "open", "high", "low", "close", "volume"]].rename(
        columns={
            "open": "signal_open",
            "high": "signal_high",
            "low": "signal_low",
            "close": "signal_close",
            "volume": "signal_volume",
        }
    )
    merged = raw.merge(sig, on=["date", "symbol"], how="left", validate="one_to_one")
    missing_signal = merged[["signal_open", "signal_high", "signal_low", "signal_close"]].isna().any(axis=1)
    if missing_signal.any():
        dates = merged.loc[missing_signal, "date"].dt.date.astype(str).tolist()
        raise ValueError(f"missing signal-adjusted rows for {symbol}: {dates[:5]}")

    merged["openinterest"] = 0
    merged = merged.rename(columns={"date": "datetime"}).set_index("datetime")
    return merged.sort_index()


def load_for_backtrader(
    cache: ParquetCache,
    symbol: str,
    *,
    start: str | None = None,
    end: str | None = None,
    source: str = SOURCE_BAOSTOCK,
    price_mode: Adjust = "raw",
    dataname: str | None = None,
) -> Any:
    try:
        import backtrader as bt
    except ImportError as exc:
        raise RuntimeError(
            "backtrader is required for load_for_backtrader; install with quant-backtest[validation]"
        ) from exc

    frame = load_backtrader_frame(
        cache,
        symbol,
        start=start,
        end=end,
        source=source,
        price_mode=price_mode,
    )
    return bt.feeds.PandasData(dataname=frame, name=dataname or symbol)
