from __future__ import annotations

import pytest

from quant_backtest.backtest import (
    BacktraderConfig,
    BacktraderEngine,
    BacktraderRunner,
    get_precomputed_selector_strategy_class,
    get_signal_sma_cross_strategy_class,
    get_three_falling_buy_three_rising_sell_strategy_class,
    get_three_rising_hold_one_day_strategy_class,
)
from quant_backtest.data.cache import ParquetCache
from tests.conftest import make_bars


def test_backtrader_engine_runs_builtin_sma_strategy_with_qfq_signal_raw_execution(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("000001.SZ", adjust="qfq", rows=40)
    raw = make_bars("000001.SZ", adjust="raw", rows=40)
    for field in ["open", "high", "low", "close"]:
        qfq[field] = [10 + idx for idx in range(40)]
        raw[field] = [100 + idx for idx in range(40)]
    cache.write(qfq)
    cache.write(raw)

    config = BacktraderConfig(
        symbols=["000001.SZ"],
        cash=100_000,
        commission_bps=0,
        slippage_bps=0,
        strategy_kwargs={"fast_period": 2, "slow_period": 3, "target_percent": 0.5},
    )
    result = BacktraderEngine(cache).run(get_signal_sma_cross_strategy_class(), config)

    assert result.metrics["start_cash"] == pytest.approx(100_000)
    assert result.metrics["final_value"] is not None
    assert len(result.equity_curve) == 40
    assert result.metrics["order_count"] >= 1
    assert not result.orders.empty
    completed = result.orders[result.orders["status"].eq("Completed")]
    assert completed["executed_price"].iloc[0] >= 100


def test_backtrader_runner_returns_normalized_result(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=10))
    cache.write(make_bars("000001.SZ", adjust="raw", rows=10))

    result = BacktraderRunner(cache).run(
        get_signal_sma_cross_strategy_class(),
        ["000001.SZ"],
        cash=50_000,
        strategy_kwargs={"fast_period": 2, "slow_period": 3},
    )

    assert result.start_cash == pytest.approx(50_000)
    assert {"metrics", "equity_curve", "orders", "trades"} == set(result.to_frames())


def test_three_rising_strategy_buys_third_close_and_sells_next_close(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("603986.SH", adjust="qfq", rows=6)
    raw = make_bars("603986.SH", adjust="raw", rows=6)

    qfq["open"] = [10, 11, 12, 13, 12, 11]
    qfq["close"] = [11, 12, 13, 12, 11, 10]
    for field in ["open", "high", "low", "close"]:
        raw[field] = [100, 101, 102, 103, 104, 105]
    raw["high"] = raw["close"] + 1
    raw["low"] = raw["close"] - 1

    cache.write(qfq)
    cache.write(raw)
    config = BacktraderConfig(
        symbols=["603986.SH"],
        cash=100_000,
        commission_bps=0,
        slippage_bps=0,
        execution_timing="same_close",
        strategy_kwargs={"target_percent": 0.95, "hold_bars": 1},
    )
    result = BacktraderEngine(cache).run(
        get_three_rising_hold_one_day_strategy_class(),
        config,
    )

    completed = result.orders[result.orders["status"].eq("Completed")].reset_index(drop=True)
    assert len(completed) == 2
    assert completed.loc[0, "side"] == "buy"
    assert completed.loc[0, "date"] == "2024-01-04"
    assert completed.loc[0, "executed_price"] == pytest.approx(102)
    assert completed.loc[1, "side"] == "sell"
    assert completed.loc[1, "date"] == "2024-01-05"
    assert completed.loc[1, "executed_price"] == pytest.approx(103)
    assert result.metrics["trade_count"] == 1


def test_three_falling_buy_three_rising_sell_strategy(tmp_path) -> None:
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
    config = BacktraderConfig(
        symbols=["603986.SH"],
        cash=100_000,
        commission_bps=0,
        slippage_bps=0,
        execution_timing="same_close",
        strategy_kwargs={"target_percent": 0.95, "signal_count": 3},
    )
    result = BacktraderEngine(cache).run(
        get_three_falling_buy_three_rising_sell_strategy_class(),
        config,
    )

    completed = result.orders[result.orders["status"].eq("Completed")].reset_index(drop=True)
    assert len(completed) == 2
    assert completed.loc[0, "side"] == "buy"
    assert completed.loc[0, "date"] == "2024-01-04"
    assert completed.loc[0, "executed_price"] == pytest.approx(102)
    assert completed.loc[1, "side"] == "sell"
    assert completed.loc[1, "date"] == "2024-01-12"
    assert completed.loc[1, "executed_price"] == pytest.approx(108)
    assert result.metrics["trade_count"] == 1


def test_precomputed_selector_strategy_uses_signal_dates(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("000001.SZ", adjust="qfq", rows=8)
    raw = make_bars("000001.SZ", adjust="raw", rows=8)
    raw["pre_close"] = raw["close"].shift(1).fillna(raw["pre_close"])
    cache.write(qfq)
    cache.write(raw)

    config = BacktraderConfig(
        symbols=["000001.SZ"],
        cash=100_000,
        commission_bps=0,
        slippage_bps=0,
        execution_timing="same_close",
        strategy_kwargs={
            "signals_by_symbol": {"000001.SZ": {"2024-01-04"}},
            "target_percent": 0.2,
            "hold_bars": 2,
            "max_positions": 1,
        },
    )
    result = BacktraderEngine(cache).run(get_precomputed_selector_strategy_class(), config)

    completed = result.orders[result.orders["status"].eq("Completed")].reset_index(drop=True)
    assert len(completed) == 2
    assert completed.loc[0, "side"] == "buy"
    assert completed.loc[0, "date"] == "2024-01-04"
    assert completed.loc[1, "side"] == "sell"
    assert result.metrics["trade_count"] == 1


def test_precomputed_selector_strategy_rejects_limit_up_entry(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("000001.SZ", adjust="qfq", rows=6)
    raw = make_bars("000001.SZ", adjust="raw", rows=6)
    raw["pre_close"] = 10.0
    raw["close"] = 11.0
    raw["open"] = 11.0
    raw["high"] = 11.0
    raw["low"] = 11.0
    cache.write(qfq)
    cache.write(raw)

    config = BacktraderConfig(
        symbols=["000001.SZ"],
        cash=100_000,
        commission_bps=0,
        slippage_bps=0,
        execution_timing="same_close",
        strategy_kwargs={
            "signals_by_symbol": {"000001.SZ": {"2024-01-02", "2024-01-03"}},
            "target_percent": 0.2,
            "hold_bars": 1,
            "max_positions": 1,
        },
    )
    result = BacktraderEngine(cache).run(get_precomputed_selector_strategy_class(), config)

    assert result.orders.empty
    assert result.metrics["trade_count"] == 0
