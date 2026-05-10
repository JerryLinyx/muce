from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from quant_backtest.backtest import (
    BacktraderConfig,
    BacktraderEngine,
    get_precomputed_selector_strategy_class,
)
from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import Adjust, SOURCE_BAOSTOCK
from quant_backtest.selection.factors import FactorSelectorConfig, build_factor_table, select_candidates


@dataclass(frozen=True)
class SelectorBacktraderValidationConfig:
    symbols: list[str]
    start: str | None = None
    end: str | None = None
    source: str = SOURCE_BAOSTOCK
    signal_adjust: Adjust = "qfq"
    execution_adjust: Adjust = "raw"
    cash: float = 1_000_000.0
    commission_bps: float = 3.0
    slippage_bps: float = 5.0
    execution_timing: str = "same_close"
    hold_days: int = 5
    target_percent_per_position: float = 0.2
    max_positions: int = 1
    take_profit_pct: float | None = None
    stop_loss_pct: float | None = None
    reject_limit_up_buy: bool = True
    reject_limit_down_sell: bool = True
    top_n: int = 5
    lot_size: int = 100
    selector: FactorSelectorConfig = FactorSelectorConfig(top_n=5)


def run_selector_backtrader_validation(
    cache: ParquetCache,
    config: SelectorBacktraderValidationConfig,
) -> dict[str, Any]:
    signal_data = cache.read_many(
        source=config.source,
        adjust=config.signal_adjust,
        symbols=config.symbols,
        start=config.start,
        end=config.end,
    )
    factor_table = build_factor_table(signal_data, config.selector)
    candidates = select_candidates(factor_table, top_n=config.top_n)
    signals_by_symbol = _signals_by_symbol(candidates)
    signals_by_date = _signals_by_date(candidates)
    validation_symbols = sorted(signals_by_symbol)
    if not validation_symbols:
        return {
            "metrics": {
                "candidate_count": 0,
                "validation_symbol_count": 0,
            },
            "candidates": candidates,
            "result": None,
        }

    bt_config = BacktraderConfig(
        symbols=validation_symbols,
        start=config.start,
        end=config.end,
        cash=config.cash,
        commission_bps=config.commission_bps,
        slippage_bps=config.slippage_bps,
        source=config.source,
        signal_adjust=config.signal_adjust,
        execution_adjust=config.execution_adjust,
        execution_timing=config.execution_timing,  # type: ignore[arg-type]
        strategy_kwargs={
            "signals_by_symbol": signals_by_symbol,
            "signals_by_date": signals_by_date,
            "execution_timing": config.execution_timing,
            "target_percent": config.target_percent_per_position,
            "hold_bars": config.hold_days,
            "max_positions": config.max_positions,
            "lot_size": config.lot_size,
            "slippage_bps": config.slippage_bps,
            "take_profit_pct": config.take_profit_pct,
            "stop_loss_pct": config.stop_loss_pct,
            "reject_limit_up_buy": config.reject_limit_up_buy,
            "reject_limit_down_sell": config.reject_limit_down_sell,
        },
    )
    result = BacktraderEngine(cache).run(get_precomputed_selector_strategy_class(), bt_config)
    metrics = dict(result.metrics)
    metrics["candidate_count"] = int(len(candidates))
    metrics["validation_symbol_count"] = int(len(validation_symbols))
    metrics["hold_days"] = int(config.hold_days)
    metrics["target_percent_per_position"] = float(config.target_percent_per_position)
    metrics["max_positions"] = int(config.max_positions)
    metrics["top_n"] = int(config.top_n)
    metrics["take_profit_pct"] = config.take_profit_pct
    metrics["stop_loss_pct"] = config.stop_loss_pct
    return {
        "metrics": metrics,
        "candidates": candidates,
        "result": result,
        "signals_by_symbol": signals_by_symbol,
        "signals_by_date": signals_by_date,
    }


def _signals_by_symbol(candidates: pd.DataFrame) -> dict[str, set[str]]:
    signals: dict[str, set[str]] = {}
    if candidates.empty:
        return signals
    for row in candidates.itertuples(index=False):
        signals.setdefault(row.symbol, set()).add(pd.Timestamp(row.date).date().isoformat())
    return signals


def _signals_by_date(
    candidates: pd.DataFrame,
    *,
    trading_dates: list[pd.Timestamp] | None = None,
    entry_lag_days: int = 0,
) -> dict[str, list[str]]:
    signals: dict[str, list[str]] = {}
    if candidates.empty:
        return signals
    date_to_index = {pd.Timestamp(date): idx for idx, date in enumerate(trading_dates or [])}
    for row in candidates.itertuples(index=False):
        signal_date = pd.Timestamp(row.date)
        entry_date = signal_date
        if entry_lag_days:
            if signal_date not in date_to_index:
                continue
            entry_index = date_to_index[signal_date] + entry_lag_days
            if trading_dates is None or entry_index >= len(trading_dates):
                continue
            entry_date = pd.Timestamp(trading_dates[entry_index])
        signals.setdefault(entry_date.date().isoformat(), []).append(row.symbol)
    return signals
