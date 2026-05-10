from __future__ import annotations

from itertools import product
from typing import Any, Iterable, Mapping

import pandas as pd

from quant_backtest.backtest.vectorbt_models import VectorbtSignals, VectorbtStrategyName


def build_vectorbt_signals(
    strategy: VectorbtStrategyName,
    signal_panels: Mapping[str, pd.DataFrame],
    parameters: Mapping[str, Any],
) -> VectorbtSignals:
    if strategy == "sma-cross":
        return _build_sma_cross(signal_panels, parameters)
    if strategy == "three-rising-hold-one":
        return _build_three_rising_hold_one(signal_panels, parameters)
    if strategy == "three-falling-buy-three-rising-sell":
        return _build_three_falling_buy_three_rising_sell(signal_panels, parameters)
    raise ValueError(f"unsupported vectorbt strategy {strategy!r}")


def expand_parameter_grid(grid: Mapping[str, Iterable[Any]]) -> list[dict[str, Any]]:
    keys = list(grid)
    if not keys:
        return [{}]
    values = [list(grid[key]) for key in keys]
    return [dict(zip(keys, combo, strict=True)) for combo in product(*values)]


def _build_sma_cross(
    signal_panels: Mapping[str, pd.DataFrame],
    parameters: Mapping[str, Any],
) -> VectorbtSignals:
    close = signal_panels["close"]
    fast_period = int(parameters.get("fast_period", 5))
    slow_period = int(parameters.get("slow_period", 20))
    if fast_period >= slow_period:
        raise ValueError("fast_period must be smaller than slow_period")

    fast = close.rolling(fast_period, min_periods=fast_period).mean()
    slow = close.rolling(slow_period, min_periods=slow_period).mean()
    above = fast > slow
    previous_above = above.shift(1, fill_value=False).astype(bool)
    entries = above & ~previous_above
    exits = ~above & previous_above
    return VectorbtSignals(entries=entries, exits=exits, strategy="sma-cross", parameters=dict(parameters))


def _build_three_rising_hold_one(
    signal_panels: Mapping[str, pd.DataFrame],
    parameters: Mapping[str, Any],
) -> VectorbtSignals:
    signal_count = int(parameters.get("signal_count", 3))
    hold_bars = int(parameters.get("hold_bars", 1))
    if signal_count < 1:
        raise ValueError("signal_count must be >= 1")
    if hold_bars < 1:
        raise ValueError("hold_bars must be >= 1")

    rising = _consecutive(signal_panels["close"] > signal_panels["open"], signal_count)
    entries = rising & ~rising.shift(1, fill_value=False).astype(bool)
    exits = entries.shift(hold_bars, fill_value=False).astype(bool)
    return VectorbtSignals(
        entries=entries,
        exits=exits,
        strategy="three-rising-hold-one",
        parameters=dict(parameters),
    )


def _build_three_falling_buy_three_rising_sell(
    signal_panels: Mapping[str, pd.DataFrame],
    parameters: Mapping[str, Any],
) -> VectorbtSignals:
    signal_count = int(parameters.get("signal_count", 3))
    max_hold_days = parameters.get("max_hold_days")
    if signal_count < 1:
        raise ValueError("signal_count must be >= 1")
    if max_hold_days is not None:
        max_hold_days = int(max_hold_days)
        if max_hold_days < 1:
            raise ValueError("max_hold_days must be >= 1 or None")

    falling = _consecutive(signal_panels["close"] < signal_panels["open"], signal_count)
    rising = _consecutive(signal_panels["close"] > signal_panels["open"], signal_count)
    if parameters.get("pyramiding"):
        entries = falling
    else:
        entries = falling & ~falling.shift(1, fill_value=False).astype(bool)
    exits = rising & ~rising.shift(1, fill_value=False).astype(bool)
    if max_hold_days is not None and not parameters.get("pyramiding"):
        exits = exits | entries.shift(max_hold_days, fill_value=False).astype(bool)
    return VectorbtSignals(
        entries=entries,
        exits=exits,
        strategy="three-falling-buy-three-rising-sell",
        parameters=dict(parameters),
    )


def _consecutive(condition: pd.DataFrame, count: int) -> pd.DataFrame:
    total = condition.astype(int)
    for offset in range(1, count):
        total = total + condition.shift(offset, fill_value=False).astype(int)
    return total.eq(count)
