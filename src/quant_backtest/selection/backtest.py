from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from quant_backtest.backtest.metrics import compute_equity_metrics, value_frame_from_vectorbt
from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import Adjust, SOURCE_BAOSTOCK
from quant_backtest.selection.factors import FactorSelectorConfig, build_factor_table, select_candidates


@dataclass(frozen=True)
class SelectionBacktestConfig:
    symbols: list[str]
    start: str | None = None
    end: str | None = None
    source: str = SOURCE_BAOSTOCK
    signal_adjust: Adjust = "qfq"
    execution_adjust: Adjust = "raw"
    cash: float = 1_000_000.0
    commission_bps: float = 3.0
    slippage_bps: float = 5.0
    hold_days: int = 1
    entry_lag_days: int = 1
    target_percent_per_position: float = 0.1
    top_n: int = 20
    selector: FactorSelectorConfig = FactorSelectorConfig()

    @property
    def commission_rate(self) -> float:
        return self.commission_bps / 10_000

    @property
    def slippage_rate(self) -> float:
        return self.slippage_bps / 10_000


def run_selection_backtest(cache: ParquetCache, config: SelectionBacktestConfig) -> dict[str, Any]:
    if config.hold_days < 1:
        raise ValueError("hold_days must be >= 1")
    if config.entry_lag_days < 0:
        raise ValueError("entry_lag_days must be >= 0")
    if config.target_percent_per_position <= 0:
        raise ValueError("target_percent_per_position must be positive")

    signal_data = cache.read_many(
        source=config.source,
        adjust=config.signal_adjust,
        symbols=config.symbols,
        start=config.start,
        end=config.end,
    )
    execution_data = cache.read_many(
        source=config.source,
        adjust=config.execution_adjust,
        symbols=config.symbols,
        start=config.start,
        end=config.end,
    )
    factor_table = build_factor_table(signal_data, config.selector)
    candidates = select_candidates(factor_table, top_n=config.top_n)
    close = execution_data.pivot(index="date", columns="symbol", values="close").sort_index()
    raw_entries = _entries_from_candidates(candidates, close)
    entries = raw_entries.shift(config.entry_lag_days, fill_value=False).astype(bool)
    exits = entries.shift(config.hold_days, fill_value=False).astype(bool)
    portfolio = _portfolio_from_selection_signals(
        close,
        entries,
        exits,
        cash=config.cash,
        fees=config.commission_rate,
        slippage=config.slippage_rate,
        size=config.target_percent_per_position,
    )
    values = value_frame_from_vectorbt(portfolio)
    equity = values.sum(axis=1) if len(values.columns) > 1 else values.iloc[:, 0]
    metrics = compute_equity_metrics(equity, start_cash=config.cash)
    metrics["annual_return_pct"] = (
        metrics["annual_return"] * 100 if metrics["annual_return"] is not None else None
    )
    metrics["max_drawdown_pct"] = (
        metrics["max_drawdown"] * 100 if metrics["max_drawdown"] is not None else None
    )
    metrics["candidate_count"] = int(len(candidates))
    metrics["entry_count"] = int(entries.sum().sum())
    metrics["trade_count"] = int(portfolio.trades.count().sum())
    metrics["entry_lag_days"] = int(config.entry_lag_days)
    return {
        "metrics": metrics,
        "factor_table": factor_table,
        "candidates": candidates,
        "entries": entries,
        "exits": exits,
        "close": close,
        "portfolio": portfolio,
    }


def _entries_from_candidates(candidates: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    entries = pd.DataFrame(False, index=close.index, columns=close.columns)
    for row in candidates.itertuples(index=False):
        if row.date in entries.index and row.symbol in entries.columns:
            entries.loc[row.date, row.symbol] = True
    return entries


def _portfolio_from_selection_signals(
    close: pd.DataFrame,
    entries: pd.DataFrame,
    exits: pd.DataFrame,
    *,
    cash: float,
    fees: float,
    slippage: float,
    size: float,
) -> Any:
    try:
        import vectorbt as vbt
    except ImportError as exc:
        raise RuntimeError("vectorbt is required for selector backtests") from exc
    return vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=cash,
        cash_sharing=True,
        size=size,
        size_type="percent",
        fees=fees,
        slippage=slippage,
        freq="1D",
    )
