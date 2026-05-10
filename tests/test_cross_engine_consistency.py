from __future__ import annotations

import pytest

from quant_backtest.backtest import (
    BacktraderConfig,
    BacktraderEngine,
    VectorbtConfig,
    VectorbtEngine,
    get_three_falling_buy_three_rising_sell_strategy_class,
)
from quant_backtest.data.cache import ParquetCache
from tests.conftest import make_bars


def test_backtrader_and_vectorbt_core_metrics_match_on_simple_close_execution(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("603986.SH", adjust="qfq", rows=10)
    raw = make_bars("603986.SH", adjust="raw", rows=10)

    qfq["open"] = [13, 12, 11, 10, 9, 8, 9, 10, 11, 12]
    qfq["close"] = [12, 11, 10, 9, 8, 7, 10, 11, 12, 11]
    for field in ["open", "high", "low", "close"]:
        raw[field] = [100 + idx for idx in range(10)]
    raw["high"] = raw["close"] + 1
    raw["low"] = raw["close"] - 1
    cache.write(qfq)
    cache.write(raw)

    common = {
        "symbols": ["603986.SH"],
        "cash": 100_000,
        "commission_bps": 0,
        "slippage_bps": 0,
        "strategy_kwargs": {"target_percent": 0.95, "signal_count": 3},
    }
    bt_result = BacktraderEngine(cache).run(
        get_three_falling_buy_three_rising_sell_strategy_class(),
        BacktraderConfig(execution_timing="same_close", **common),
    )
    vbt_result = VectorbtEngine(cache).run(
        VectorbtConfig(strategy="three-falling-buy-three-rising-sell", **common),
    )
    vbt_metrics = vbt_result.metrics.iloc[0].to_dict()

    for metric in ["final_value", "total_return", "annual_return", "max_drawdown", "sharpe"]:
        assert bt_result.metrics[metric] == pytest.approx(vbt_metrics[metric], rel=1e-10, abs=1e-10)
    assert bt_result.metrics["trade_count"] == vbt_metrics["trade_count"]


def test_backtrader_and_vectorbt_metrics_are_close_on_cached_real_data_if_available() -> None:
    cache = ParquetCache()
    if "603986.SH" not in cache.available_symbols(adjust="qfq"):
        pytest.skip("603986.SH qfq cache is not available")
    if "603986.SH" not in cache.available_symbols(adjust="raw"):
        pytest.skip("603986.SH raw cache is not available")

    common = {
        "symbols": ["603986.SH"],
        "start": "20250507",
        "end": "20260507",
        "cash": 1_000_000,
        "commission_bps": 3,
        "slippage_bps": 5,
        "strategy_kwargs": {"target_percent": 0.95, "signal_count": 3},
    }
    bt_result = BacktraderEngine(cache).run(
        get_three_falling_buy_three_rising_sell_strategy_class(),
        BacktraderConfig(execution_timing="same_close", **common),
    )
    vbt_result = VectorbtEngine(cache).run(
        VectorbtConfig(strategy="three-falling-buy-three-rising-sell", **common),
    )
    vbt_metrics = vbt_result.metrics.iloc[0].to_dict()

    assert bt_result.metrics["total_return"] == pytest.approx(vbt_metrics["total_return"], abs=0.002)
    assert bt_result.metrics["max_drawdown"] == pytest.approx(vbt_metrics["max_drawdown"], abs=0.002)
    assert bt_result.metrics["trade_count"] == vbt_metrics["trade_count"]
