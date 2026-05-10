from __future__ import annotations

import json
import sys

import pandas as pd
import pytest

from quant_backtest.cli_selection import main as selection_main
from quant_backtest.data.cache import ParquetCache
from quant_backtest.selection import (
    FactorSelectorConfig,
    SelectionBacktestConfig,
    SelectionExecutionConfig,
    SelectionHitRateConfig,
    SelectorBacktraderValidationConfig,
    SelectorValidationGapConfig,
    build_factor_table,
    evaluate_candidate_hit_rate,
    run_selection_backtest,
    run_selection_execution_simulation,
    run_selection_hit_rate,
    run_selector_backtrader_validation,
    run_selector_validation_gap,
    select_candidates,
    sweep_selection_execution,
    sweep_selection_hit_rate,
)
from quant_backtest.selection.diagnostics import compare_order_summaries
from tests.conftest import make_bars


def test_build_factor_table_and_select_candidates(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    bars = make_selector_bars("603986.SH", rows=90)
    cache.write(bars)

    factor_table = build_factor_table(
        cache.read_symbol(source="baostock", adjust="qfq", symbol="603986.SH"),
        FactorSelectorConfig(min_score=1, top_n=5, volume_multiplier=1.1),
    )
    candidates = select_candidates(factor_table, top_n=5)

    assert "factor_score" in factor_table.columns
    assert "macd_golden_cross" in factor_table.columns
    assert "volume_breakout" in factor_table.columns
    assert not candidates.empty
    assert candidates["factor_score"].min() >= 1


def test_selector_can_require_specific_factors(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    bars = make_selector_bars("603986.SH", rows=90)
    cache.write(bars)

    factor_table = build_factor_table(
        cache.read_symbol(source="baostock", adjust="qfq", symbol="603986.SH"),
        FactorSelectorConfig(min_score=1, top_n=5, volume_multiplier=1.1, require_factors=("volume_breakout",)),
    )
    candidates = select_candidates(factor_table, top_n=5)

    assert not candidates.empty
    assert candidates["volume_breakout"].all()


def test_selector_rejects_unknown_required_factor(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    bars = make_selector_bars("603986.SH", rows=90)
    cache.write(bars)

    with pytest.raises(ValueError, match="unknown selector factors"):
        build_factor_table(
            cache.read_symbol(source="baostock", adjust="qfq", symbol="603986.SH"),
            FactorSelectorConfig(require_factors=("not_a_factor",)),
        )


def test_selection_backtest_runs_on_cached_qfq_and_raw(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_selector_bars("603986.SH", rows=90, adjust="qfq")
    raw = make_selector_bars("603986.SH", rows=90, adjust="raw")
    cache.write(qfq)
    cache.write(raw)

    result = run_selection_backtest(
        cache,
        SelectionBacktestConfig(
            symbols=["603986.SH"],
            cash=100_000,
            hold_days=2,
            target_percent_per_position=0.5,
            top_n=1,
            commission_bps=0,
            slippage_bps=0,
            selector=FactorSelectorConfig(min_score=1, top_n=1, volume_multiplier=1.1),
        ),
    )

    assert result["metrics"]["candidate_count"] > 0
    assert result["metrics"]["entry_count"] > 0
    assert result["metrics"]["entry_lag_days"] == 1
    assert result["metrics"]["final_value"] is not None


def test_selection_execution_simulation_runs_with_lot_sizing(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))

    result = run_selection_execution_simulation(
        cache,
        SelectionExecutionConfig(
            symbols=["603986.SH"],
            cash=100_000,
            hold_days=2,
            target_percent_per_position=0.5,
            top_n=1,
            commission_bps=0,
            slippage_bps=0,
            selector=FactorSelectorConfig(min_score=1, top_n=1, volume_multiplier=1.1),
        ),
    )

    assert result["metrics"]["final_value"] is not None
    assert result["metrics"]["filled_buy_count"] >= 1
    assert result["orders"]["shares"].max() % 100 == 0


def test_selection_execution_simulation_rejects_limit_up_buys(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_selector_bars("603986.SH", rows=90, adjust="qfq")
    raw = make_selector_bars("603986.SH", rows=90, adjust="raw")
    raw["pre_close"] = 10.0
    raw["open"] = 11.0
    raw["high"] = 11.0
    raw["low"] = 11.0
    raw["close"] = 11.0
    raw["amount"] = raw["volume"] * raw["close"]
    cache.write(qfq)
    cache.write(raw)

    result = run_selection_execution_simulation(
        cache,
        SelectionExecutionConfig(
            symbols=["603986.SH"],
            cash=100_000,
            top_n=1,
            selector=FactorSelectorConfig(min_score=1, top_n=1, volume_multiplier=1.1),
        ),
    )

    assert result["metrics"]["filled_buy_count"] == 0
    assert result["metrics"]["limit_up_buy_rejections"] >= 1


def test_sweep_selection_execution_runs_grid(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))

    table = sweep_selection_execution(
        cache,
        SelectionExecutionConfig(
            symbols=["603986.SH"],
            cash=100_000,
            top_n=1,
            commission_bps=0,
            slippage_bps=0,
            selector=FactorSelectorConfig(min_score=1, top_n=1, volume_multiplier=1.1),
        ),
        hold_days=[1, 2],
        target_percents=[0.2, 0.5],
        max_positions=[1],
        top_ns=[1],
        stop_losses=[None],
        take_profits=[None],
        entry_lag_days=[0],
        rsi_thresholds=[50, 55],
    )

    assert len(table) == 8
    assert set(table["hold_days"]) == {1, 2}
    assert set(table["rsi_threshold"]) == {50, 55}
    assert "final_value" in table.columns


def test_compare_order_summaries_classifies_sizing_and_price_diffs() -> None:
    simulator_orders = pd.DataFrame(
        [
            {
                "date": "2026-01-02",
                "symbol": "603986.SH",
                "side": "buy",
                "status": "filled",
                "reason": "entry",
                "shares": 100,
                "price": 10.0,
                "commission": 1.0,
            }
        ]
    )
    backtrader_orders = pd.DataFrame(
        [
            {
                "date": "2026-01-02",
                "symbol": "603986.SH",
                "side": "buy",
                "status": "filled",
                "reason": "filled",
                "shares": 200,
                "price": 10.5,
                "commission": 1.0,
            }
        ]
    )

    comparison = compare_order_summaries(
        simulator_orders,
        backtrader_orders,
        price_abs_tolerance=0.01,
        share_abs_tolerance=0.01,
    )

    assert comparison.iloc[0]["category"] == "sizing_and_fill_price"


def test_selector_validation_gap_runs_and_reports_summary(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))

    result = run_selector_validation_gap(
        cache,
        SelectorValidationGapConfig(
            symbols=["603986.SH"],
            cash=100_000,
            top_n=1,
            hold_days=2,
            target_percent_per_position=0.2,
            commission_bps=0,
            slippage_bps=0,
            selector=FactorSelectorConfig(min_score=1, top_n=1, volume_multiplier=1.1),
        ),
    )

    assert "total_return_diff" in result["summary"]
    assert "order_comparison" in result["artifacts"]
    assert "equity_comparison" in result["artifacts"]


def test_selector_backtrader_validation_runs_on_candidate_symbols(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))

    result = run_selector_backtrader_validation(
        cache,
        SelectorBacktraderValidationConfig(
            symbols=["603986.SH"],
            cash=100_000,
            commission_bps=0,
            slippage_bps=0,
            hold_days=2,
            target_percent_per_position=0.2,
            top_n=1,
            selector=FactorSelectorConfig(min_score=1, top_n=1, volume_multiplier=1.1),
        ),
    )

    assert result["metrics"]["candidate_count"] > 0
    assert result["metrics"]["validation_symbol_count"] == 1
    assert result["result"] is not None


def test_evaluate_candidate_hit_rate_uses_next_close() -> None:
    execution = pd.concat(
        [
            make_bars("000001.SZ", rows=3, adjust="raw"),
            make_bars("600000.SH", rows=3, adjust="raw"),
        ],
        ignore_index=True,
    )
    execution.loc[execution["symbol"].eq("000001.SZ"), "close"] = [10.0, 11.0, 12.0]
    execution.loc[execution["symbol"].eq("600000.SH"), "close"] = [20.0, 19.0, 18.0]
    candidates = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2024-01-02"),
                "symbol": "000001.SZ",
                "factor_score": 3,
                "factor_reasons": "unit_test",
            },
            {
                "date": pd.Timestamp("2024-01-02"),
                "symbol": "600000.SH",
                "factor_score": 2,
                "factor_reasons": "unit_test",
            },
            {
                "date": pd.Timestamp("2024-01-04"),
                "symbol": "000001.SZ",
                "factor_score": 1,
                "factor_reasons": "unit_test",
            },
        ]
    )

    evaluated = evaluate_candidate_hit_rate(candidates, execution, forward_days=1)

    assert evaluated["is_win"].sum() == 1
    assert evaluated["is_loss"].sum() == 1
    assert evaluated["outcome"].eq("invalid").sum() == 1


def test_selection_hit_rate_runs_on_cached_qfq_and_raw(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_selector_bars("603986.SH", rows=90, adjust="qfq")
    raw = make_selector_bars("603986.SH", rows=90, adjust="raw")
    cache.write(qfq)
    cache.write(raw)

    result = run_selection_hit_rate(
        cache,
        SelectionHitRateConfig(
            symbols=["603986.SH"],
            top_n=1,
            selector=FactorSelectorConfig(min_score=1, top_n=1, volume_multiplier=1.1),
        ),
    )

    assert result["metrics"]["total_signals"] > 0
    assert result["metrics"]["valid_signals"] > 0
    assert "win_rate" in result["metrics"]
    assert not result["daily_summary"].empty


def test_sweep_hit_rate_preserves_required_factors(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))

    table = sweep_selection_hit_rate(
        cache,
        SelectionHitRateConfig(
            symbols=["603986.SH"],
            selector=FactorSelectorConfig(
                min_score=1,
                top_n=5,
                volume_multiplier=1.1,
                require_factors=("volume_breakout",),
            ),
        ),
        top_ns=[5],
        min_scores=[1],
        rsi_thresholds=[55],
        volume_multipliers=[1.1],
    )
    strict = run_selection_hit_rate(
        cache,
        SelectionHitRateConfig(
            symbols=["603986.SH"],
            top_n=5,
            selector=FactorSelectorConfig(
                min_score=1,
                top_n=5,
                volume_multiplier=1.1,
                require_factors=("volume_breakout",),
            ),
        ),
    )

    assert table.iloc[0]["valid_signals"] == strict["metrics"]["valid_signals"]


def test_quant_select_candidates_cli(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-select",
            "--cache-root",
            str(tmp_path),
            "candidates",
            "--symbols",
            "603986.SH",
            "--min-score",
            "1",
            "--top-n",
            "3",
            "--volume-multiplier",
            "1.1",
        ],
    )

    selection_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["candidate_count"] >= 1
    assert payload["candidates"][0]["symbol"] == "603986.SH"


def test_quant_select_hit_rate_cli(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-select",
            "--cache-root",
            str(tmp_path),
            "hit-rate",
            "--symbols",
            "603986.SH",
            "--min-score",
            "1",
            "--top-n",
            "1",
            "--volume-multiplier",
            "1.1",
        ],
    )

    selection_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["metrics"]["total_signals"] > 0
    assert payload["metrics"]["price_mode"] == "close_to_next_close"


def test_quant_select_attribution_cli(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-select",
            "--cache-root",
            str(tmp_path),
            "attribution",
            "--symbols",
            "603986.SH",
            "--min-score",
            "1",
            "--top-n",
            "1",
            "--volume-multiplier",
            "1.1",
            "--min-valid-count",
            "1",
        ],
    )

    selection_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["metrics"]["total_signals"] > 0
    assert "by_combo" in payload
    assert "by_factor" in payload


def test_quant_select_sweep_simulate_cli(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-select",
            "--cache-root",
            str(tmp_path),
            "sweep-simulate",
            "--symbols",
            "603986.SH",
            "--min-score",
            "1",
            "--top-n-list",
            "1",
            "--hold-days-list",
            "1,2",
            "--target-percent-list",
            "20",
            "--max-positions-list",
            "1",
            "--volume-multiplier",
            "1.1",
            "--rsi-threshold-list",
            "50,55",
            "--limit",
            "2",
        ],
    )

    selection_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["row_count"] == 4
    assert payload["rows"]
    assert "rsi_threshold" in payload["rows"][0]


def test_quant_select_validate_backtrader_cli(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-select",
            "--cache-root",
            str(tmp_path),
            "validate-backtrader",
            "--symbols",
            "603986.SH",
            "--min-score",
            "1",
            "--top-n",
            "1",
            "--volume-multiplier",
            "1.1",
            "--hold-days",
            "2",
            "--target-percent-per-position",
            "20",
        ],
    )

    selection_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["metrics"]["candidate_count"] > 0
    assert payload["validation_symbol_count"] == 1


def test_quant_select_diagnose_validation_gap_cli(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="qfq"))
    cache.write(make_selector_bars("603986.SH", rows=90, adjust="raw"))
    out = tmp_path / "gap-report"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-select",
            "--cache-root",
            str(tmp_path),
            "diagnose-validation-gap",
            "--symbols",
            "603986.SH",
            "--min-score",
            "1",
            "--top-n",
            "1",
            "--volume-multiplier",
            "1.1",
            "--hold-days",
            "2",
            "--target-percent-per-position",
            "20",
            "--out",
            str(out),
        ],
    )

    selection_main()
    payload = json.loads(capsys.readouterr().out)
    assert "total_return_diff" in payload["summary"]
    assert (out / "summary.json").exists()
    assert (out / "order_comparison.csv").exists()


def make_selector_bars(symbol: str, *, rows: int, adjust: str = "qfq"):
    bars = make_bars(symbol, adjust=adjust, rows=rows)
    closes = []
    for idx in range(rows):
        if idx < rows - 8:
            closes.append(20.0 + idx * 0.05)
        else:
            closes.append(24.0 + (idx - (rows - 8)) * 1.2)
    bars["close"] = closes
    bars["open"] = bars["close"] - 0.2
    bars["high"] = bars["close"] + 0.5
    bars["low"] = bars["close"] - 0.5
    bars["volume"] = [1000.0] * (rows - 2) + [5000.0, 6000.0]
    bars["amount"] = bars["volume"] * bars["close"]
    return bars
