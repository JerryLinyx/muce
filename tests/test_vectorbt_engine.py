from __future__ import annotations

import json
import sys

import pytest

from quant_backtest.backtest import VectorbtConfig, VectorbtEngine, VectorbtRunner
from quant_backtest.backtest.vectorbt_strategies import (
    build_vectorbt_signals,
    expand_parameter_grid,
)
from quant_backtest.cli_backtest import main as backtest_main
from quant_backtest.data.adapters import load_for_vectorbt
from quant_backtest.data.cache import ParquetCache
from tests.conftest import make_bars


def test_expand_parameter_grid() -> None:
    assert expand_parameter_grid({"a": [1, 2], "b": [3, 4]}) == [
        {"a": 1, "b": 3},
        {"a": 1, "b": 4},
        {"a": 2, "b": 3},
        {"a": 2, "b": 4},
    ]


def test_vectorbt_three_falling_buy_three_rising_sell_signals(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("603986.SH", adjust="qfq", rows=10)
    qfq["open"] = [13, 12, 11, 10, 9, 8, 9, 10, 11, 12]
    qfq["close"] = [12, 11, 10, 9, 8, 7, 10, 11, 12, 11]
    cache.write(qfq)

    panels = load_for_vectorbt(cache, ["603986.SH"], adjust="qfq")
    signals = build_vectorbt_signals(
        "three-falling-buy-three-rising-sell",
        panels,
        {"signal_count": 3, "target_percent": 0.95},
    )

    entries = signals.entries["603986.SH"]
    exits = signals.exits["603986.SH"]
    assert entries[entries].index[0].date().isoformat() == "2024-01-04"
    assert exits[exits].index[0].date().isoformat() == "2024-01-12"


def test_vectorbt_three_falling_strategy_max_hold_days_adds_exit(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("603986.SH", adjust="qfq", rows=8)
    qfq["open"] = [13, 12, 11, 10, 10, 10, 10, 10]
    qfq["close"] = [12, 11, 10, 9, 9, 9, 9, 9]
    cache.write(qfq)

    panels = load_for_vectorbt(cache, ["603986.SH"], adjust="qfq")
    signals = build_vectorbt_signals(
        "three-falling-buy-three-rising-sell",
        panels,
        {"signal_count": 3, "max_hold_days": 2, "target_percent": 0.95},
    )

    exits = signals.exits["603986.SH"]
    assert exits[exits].index[0].date().isoformat() == "2024-01-08"


def test_vectorbt_engine_runs_and_sweeps(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("603986.SH", adjust="qfq", rows=40)
    raw = make_bars("603986.SH", adjust="raw", rows=40)
    for field in ["open", "high", "low", "close"]:
        qfq[field] = [10 + idx for idx in range(40)]
        raw[field] = [100 + idx for idx in range(40)]
    cache.write(qfq)
    cache.write(raw)

    config = VectorbtConfig(
        symbols=["603986.SH"],
        strategy="sma-cross",
        cash=100_000,
        commission_bps=0,
        slippage_bps=0,
        strategy_kwargs={"target_percent": 0.5},
    )
    result = VectorbtEngine(cache).sweep(
        config,
        {"fast_period": [2, 3], "slow_period": [5], "target_percent": [0.5]},
    )

    assert len(result.metrics) == 2
    assert set(result.metrics["param_fast_period"]) == {2, 3}
    assert result.metrics["final_value"].min() > 100_000
    assert list(result.entries.columns.names) == ["parameter_index", "symbol"]


def test_vectorbt_sweep_supports_risk_controls(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("603986.SH", adjust="qfq", rows=20)
    raw = make_bars("603986.SH", adjust="raw", rows=20)
    qfq["open"] = [13, 12, 11, 10, 9, 8, 9, 10, 11, 12] * 2
    qfq["close"] = [12, 11, 10, 9, 8, 7, 10, 11, 12, 11] * 2
    raw["close"] = [100, 101, 102, 90, 92, 95, 104, 108, 111, 112] * 2
    raw["open"] = raw["close"]
    raw["high"] = raw["close"] + 1
    raw["low"] = raw["close"] - 1
    cache.write(qfq)
    cache.write(raw)

    config = VectorbtConfig(
        symbols=["603986.SH"],
        strategy="three-falling-buy-three-rising-sell",
        cash=100_000,
        commission_bps=0,
        slippage_bps=0,
        strategy_kwargs={},
    )
    result = VectorbtEngine(cache).sweep(
        config,
        {
            "target_percent": [0.05, 0.10],
            "max_hold_days": [1, 2],
            "stop_loss": [None, -0.05],
            "take_profit": [None, 0.05],
            "signal_count": [3],
        },
    )

    assert len(result.metrics) == 16
    assert set(result.metrics["param_target_percent"]) == {0.05, 0.10}
    assert set(result.metrics["param_max_hold_days"]) == {1, 2}
    assert result.metrics["param_stop_loss"].isna().any()
    assert result.metrics["param_take_profit"].isna().any()


def test_vectorbt_sweep_supports_pyramiding_target_orders(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("603986.SH", adjust="qfq", rows=14)
    raw = make_bars("603986.SH", adjust="raw", rows=14)
    qfq["open"] = [13, 12, 11, 10, 9, 9, 9, 9, 8, 7, 10, 11, 12, 13]
    qfq["close"] = [12, 11, 10, 9, 8, 10, 8, 8, 7, 6, 11, 12, 13, 14]
    for field in ["open", "high", "low", "close"]:
        raw[field] = [100 + idx for idx in range(14)]
    raw["high"] = raw["close"] + 1
    raw["low"] = raw["close"] - 1
    cache.write(qfq)
    cache.write(raw)

    config = VectorbtConfig(
        symbols=["603986.SH"],
        strategy="three-falling-buy-three-rising-sell",
        cash=100_000,
        commission_bps=0,
        slippage_bps=0,
        strategy_kwargs={},
    )
    result = VectorbtEngine(cache).sweep(
        config,
        {
            "target_percent": [0.2],
            "max_position_percent": [0.6],
            "pyramiding": [True],
            "max_hold_days": [None],
            "stop_loss": [None],
            "take_profit": [None],
            "signal_count": [3],
        },
    )

    portfolio = result.portfolio[0]
    orders = portfolio.orders.records_readable
    buy_orders = orders[orders["Side"].eq("Buy")]
    assert len(result.metrics) == 1
    assert bool(result.metrics.iloc[0]["param_pyramiding"]) is True
    assert len(buy_orders) == 3
    assert portfolio.cash().min().iloc[0] >= 0


def test_vectorbt_runner_returns_normalized_result(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("603986.SH", adjust="qfq", rows=10))
    cache.write(make_bars("603986.SH", adjust="raw", rows=10))

    result = VectorbtRunner(cache).run(
        strategy="three-rising-hold-one",
        symbols=["603986.SH"],
        strategy_kwargs={"signal_count": 3, "hold_bars": 1, "target_percent": 0.95},
    )

    assert result.strategy == "three-rising-hold-one"
    assert len(result.metrics) == 1
    assert "total_return" in result.metrics.columns


def test_quant_backtest_sweep_cli_outputs_ranked_metrics(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("603986.SH", adjust="qfq", rows=30))
    cache.write(make_bars("603986.SH", adjust="raw", rows=30))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-backtest",
            "--cache-root",
            str(tmp_path),
            "sweep",
            "--symbols",
            "603986.SH",
            "--strategy",
            "three-rising-hold-one",
            "--signal-counts",
            "2,3",
            "--hold-bars-list",
            "1",
            "--target-percents",
            "5,10",
        ],
    )

    backtest_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["strategy"] == "three-rising-hold-one"
    assert payload["row_count"] == 4
    assert len(payload["metrics"]) == 4
    assert "total_return" in payload["metrics"][0]
