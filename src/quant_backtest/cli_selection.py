from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import SOURCE_BAOSTOCK
from quant_backtest.selection import (
    FactorSelectorConfig,
    SelectionBacktestConfig,
    SelectionExecutionConfig,
    SelectionHitRateConfig,
    SelectorBacktraderValidationConfig,
    SelectorValidationGapConfig,
    build_factor_table,
    run_selection_backtest,
    run_selection_execution_simulation,
    run_selection_hit_rate,
    run_selector_backtrader_validation,
    run_selector_validation_gap,
    select_candidates,
    summarize_factor_attribution,
    sweep_selection_execution,
    sweep_selection_hit_rate,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="quant-select")
    parser.add_argument("--cache-root", default="data/cache/a_share/daily")
    subparsers = parser.add_subparsers(dest="command", required=True)

    candidates = subparsers.add_parser("candidates")
    _add_common_args(candidates)
    candidates.add_argument("--date")

    backtest = subparsers.add_parser("backtest")
    _add_common_args(backtest)
    backtest.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    backtest.add_argument("--cash", type=float, default=1_000_000)
    backtest.add_argument("--commission-bps", type=float, default=3.0)
    backtest.add_argument("--slippage-bps", type=float, default=5.0)
    backtest.add_argument("--hold-days", type=int, default=1)
    backtest.add_argument("--entry-lag-days", type=int, default=1)
    backtest.add_argument("--target-percent-per-position", type=float, default=10.0)

    simulate = subparsers.add_parser("simulate")
    _add_common_args(simulate)
    simulate.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    simulate.add_argument("--cash", type=float, default=1_000_000)
    simulate.add_argument("--commission-bps", type=float, default=3.0)
    simulate.add_argument("--slippage-bps", type=float, default=5.0)
    simulate.add_argument("--surge-threshold-pct", type=float, default=3.0)
    simulate.add_argument("--surge-extra-slippage-bps", type=float, default=20.0)
    simulate.add_argument("--hold-days", type=int, default=1)
    simulate.add_argument("--entry-lag-days", type=int, default=0)
    simulate.add_argument("--entry-price-field", default="close", choices=["open", "close"])
    simulate.add_argument("--exit-price-field", default="close", choices=["open", "close"])
    simulate.add_argument("--target-percent-per-position", type=float, default=10.0)
    simulate.add_argument("--max-positions", type=int, default=1)
    simulate.add_argument("--lot-size", type=int, default=100)
    simulate.add_argument("--allow-limit-up-buy", action="store_true")
    simulate.add_argument("--allow-limit-down-sell", action="store_true")
    simulate.add_argument("--take-profit-pct", type=float)
    simulate.add_argument("--stop-loss-pct", type=float)
    simulate.add_argument("--order-limit", type=int, default=20)

    validate_bt = subparsers.add_parser("validate-backtrader")
    _add_common_args(validate_bt)
    validate_bt.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    validate_bt.add_argument("--cash", type=float, default=1_000_000)
    validate_bt.add_argument("--commission-bps", type=float, default=3.0)
    validate_bt.add_argument("--slippage-bps", type=float, default=5.0)
    validate_bt.add_argument("--execution-timing", default="same_close", choices=["same_close", "next_open"])
    validate_bt.add_argument("--hold-days", type=int, default=5)
    validate_bt.add_argument("--target-percent-per-position", type=float, default=20.0)
    validate_bt.add_argument("--max-positions", type=int, default=1)
    validate_bt.add_argument("--lot-size", type=int, default=100)
    validate_bt.add_argument("--allow-limit-up-buy", action="store_true")
    validate_bt.add_argument("--allow-limit-down-sell", action="store_true")
    validate_bt.add_argument("--take-profit-pct", type=float)
    validate_bt.add_argument("--stop-loss-pct", type=float)
    validate_bt.add_argument("--order-limit", type=int, default=20)

    diagnose_gap = subparsers.add_parser("diagnose-validation-gap")
    _add_common_args(diagnose_gap)
    diagnose_gap.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    diagnose_gap.add_argument("--cash", type=float, default=1_000_000)
    diagnose_gap.add_argument("--commission-bps", type=float, default=3.0)
    diagnose_gap.add_argument("--slippage-bps", type=float, default=5.0)
    diagnose_gap.add_argument("--execution-timing", default="same_close", choices=["same_close", "next_open"])
    diagnose_gap.add_argument("--hold-days", type=int, default=5)
    diagnose_gap.add_argument("--target-percent-per-position", type=float, default=20.0)
    diagnose_gap.add_argument("--max-positions", type=int, default=1)
    diagnose_gap.add_argument("--lot-size", type=int, default=100)
    diagnose_gap.add_argument("--allow-limit-up-buy", action="store_true")
    diagnose_gap.add_argument("--allow-limit-down-sell", action="store_true")
    diagnose_gap.add_argument("--take-profit-pct", type=float)
    diagnose_gap.add_argument("--stop-loss-pct", type=float)
    diagnose_gap.add_argument("--out")
    diagnose_gap.add_argument("--preview-limit", type=int, default=10)

    sweep_simulate = subparsers.add_parser("sweep-simulate")
    _add_common_args(sweep_simulate)
    sweep_simulate.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    sweep_simulate.add_argument("--cash", type=float, default=1_000_000)
    sweep_simulate.add_argument("--commission-bps", type=float, default=3.0)
    sweep_simulate.add_argument("--slippage-bps", type=float, default=5.0)
    sweep_simulate.add_argument("--surge-threshold-pct", type=float, default=3.0)
    sweep_simulate.add_argument("--surge-extra-slippage-bps", type=float, default=20.0)
    sweep_simulate.add_argument("--hold-days-list", default="1,2,3,4,5")
    sweep_simulate.add_argument("--entry-lag-days-list", default="0")
    sweep_simulate.add_argument("--entry-price-field", default="close", choices=["open", "close"])
    sweep_simulate.add_argument("--exit-price-field", default="close", choices=["open", "close"])
    sweep_simulate.add_argument("--target-percent-list", default="5,10,20,30")
    sweep_simulate.add_argument("--max-positions-list", default="1,2,3,5")
    sweep_simulate.add_argument("--top-n-list", default="1,2,5")
    sweep_simulate.add_argument("--lot-size", type=int, default=100)
    sweep_simulate.add_argument("--allow-limit-up-buy", action="store_true")
    sweep_simulate.add_argument("--allow-limit-down-sell", action="store_true")
    sweep_simulate.add_argument("--take-profit-list", default="none")
    sweep_simulate.add_argument("--stop-loss-list", default="none")
    sweep_simulate.add_argument("--min-score-list", default="")
    sweep_simulate.add_argument("--rsi-threshold-list", default="")
    sweep_simulate.add_argument("--volume-multiplier-list", default="")
    sweep_simulate.add_argument("--boll-std-list", default="")
    sweep_simulate.add_argument(
        "--rank-by",
        default="sharpe",
        choices=["sharpe", "total_return", "annual_return", "max_drawdown", "trade_win_rate"],
    )
    sweep_simulate.add_argument("--limit", type=int, default=20)

    hit_rate = subparsers.add_parser("hit-rate")
    _add_common_args(hit_rate)
    hit_rate.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    hit_rate.add_argument("--forward-days", type=int, default=1)
    hit_rate.add_argument(
        "--price-mode",
        default="close_to_next_close",
        choices=["close_to_next_close", "next_open_to_next_close"],
    )
    hit_rate.add_argument("--daily-limit", type=int, default=20)

    attribution = subparsers.add_parser("attribution")
    _add_common_args(attribution)
    attribution.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    attribution.add_argument("--forward-days", type=int, default=1)
    attribution.add_argument(
        "--price-mode",
        default="close_to_next_close",
        choices=["close_to_next_close", "next_open_to_next_close"],
    )
    attribution.add_argument("--min-valid-count", type=int, default=30)
    attribution.add_argument("--limit", type=int, default=20)

    sweep = subparsers.add_parser("sweep-hit-rate")
    _add_common_args(sweep)
    sweep.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    sweep.add_argument("--forward-days", type=int, default=1)
    sweep.add_argument(
        "--price-mode",
        default="close_to_next_close",
        choices=["close_to_next_close", "next_open_to_next_close"],
    )
    sweep.add_argument("--top-n-list", default="")
    sweep.add_argument("--min-score-list", default="")
    sweep.add_argument("--rsi-threshold-list", default="")
    sweep.add_argument("--volume-multiplier-list", default="")
    sweep.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    cache = ParquetCache(Path(args.cache_root))
    symbols = _symbols(args, cache)
    selector = _selector_config(args)

    if args.command == "candidates":
        data = cache.read_many(
            source=args.source,
            adjust=args.signal_adjust,
            symbols=symbols,
            start=args.start,
            end=args.end,
        )
        factor_table = build_factor_table(data, selector)
        selected = select_candidates(factor_table, date=args.date, top_n=args.top_n, latest=args.date is None)
        print(
            json.dumps(
                {
                    "candidate_count": len(selected),
                    "symbol_count": len(symbols),
                    "symbol_sample": symbols[:10],
                    "signal_adjust": args.signal_adjust,
                    "candidates": selected[_candidate_columns(selected)].to_dict(orient="records"),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "hit-rate":
        result = run_selection_hit_rate(
            cache,
            SelectionHitRateConfig(
                symbols=symbols,
                start=args.start,
                end=args.end,
                source=args.source,
                signal_adjust=args.signal_adjust,
                execution_adjust=args.execution_adjust,
                forward_days=args.forward_days,
                top_n=args.top_n,
                price_mode=args.price_mode,
                selector=selector,
            ),
        )
        evaluated = result["evaluated_candidates"]
        daily = result["daily_summary"]
        print(
            json.dumps(
                {
                    "metrics": result["metrics"],
                    "symbol_count": len(symbols),
                    "symbol_sample": symbols[:10],
                    "daily_summary": daily.tail(args.daily_limit).to_dict(orient="records"),
                    "preview_candidates": evaluated[_candidate_columns(evaluated)].head(args.top_n).to_dict(
                        orient="records"
                    ),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "simulate":
        result = run_selection_execution_simulation(
            cache,
            SelectionExecutionConfig(
                symbols=symbols,
                start=args.start,
                end=args.end,
                source=args.source,
                signal_adjust=args.signal_adjust,
                execution_adjust=args.execution_adjust,
                cash=args.cash,
                commission_bps=args.commission_bps,
                slippage_bps=args.slippage_bps,
                surge_threshold_pct=_normalize_optional_percent(args.surge_threshold_pct),
                surge_extra_slippage_bps=args.surge_extra_slippage_bps,
                hold_days=args.hold_days,
                entry_lag_days=args.entry_lag_days,
                entry_price_field=args.entry_price_field,
                exit_price_field=args.exit_price_field,
                target_percent_per_position=_normalize_percent(args.target_percent_per_position),
                max_positions=args.max_positions,
                lot_size=args.lot_size,
                reject_limit_up_buy=not args.allow_limit_up_buy,
                reject_limit_down_sell=not args.allow_limit_down_sell,
                take_profit_pct=_normalize_optional_percent(args.take_profit_pct),
                stop_loss_pct=_normalize_optional_percent(args.stop_loss_pct),
                top_n=args.top_n,
                selector=selector,
            ),
        )
        orders = result["orders"]
        print(
            json.dumps(
                {
                    "metrics": result["metrics"],
                    "candidate_count": len(result["candidates"]),
                    "filled_orders": orders[orders["status"].eq("filled")].tail(args.order_limit).to_dict(
                        orient="records"
                    )
                    if not orders.empty
                    else [],
                    "rejected_orders": orders[orders["status"].eq("rejected")].tail(args.order_limit).to_dict(
                        orient="records"
                    )
                    if not orders.empty
                    else [],
                    "signal_adjust": args.signal_adjust,
                    "execution_adjust": args.execution_adjust,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "validate-backtrader":
        result = run_selector_backtrader_validation(
            cache,
            SelectorBacktraderValidationConfig(
                symbols=symbols,
                start=args.start,
                end=args.end,
                source=args.source,
                signal_adjust=args.signal_adjust,
                execution_adjust=args.execution_adjust,
                cash=args.cash,
                commission_bps=args.commission_bps,
                slippage_bps=args.slippage_bps,
                execution_timing=args.execution_timing,
                hold_days=args.hold_days,
                target_percent_per_position=_normalize_percent(args.target_percent_per_position),
                max_positions=args.max_positions,
                lot_size=args.lot_size,
                take_profit_pct=_normalize_optional_percent(args.take_profit_pct),
                stop_loss_pct=_normalize_optional_percent(args.stop_loss_pct),
                reject_limit_up_buy=not args.allow_limit_up_buy,
                reject_limit_down_sell=not args.allow_limit_down_sell,
                top_n=args.top_n,
                selector=selector,
            ),
        )
        bt_result = result["result"]
        orders = bt_result.orders if bt_result is not None else None
        trades = bt_result.trades if bt_result is not None else None
        print(
            json.dumps(
                {
                    "metrics": result["metrics"],
                    "candidate_count": len(result["candidates"]),
                    "validation_symbol_count": result["metrics"].get("validation_symbol_count", 0),
                    "completed_orders": _json_records(
                        orders[orders["status"].eq("Completed")].tail(args.order_limit)
                    )
                    if orders is not None and not orders.empty
                    else [],
                    "trades": _json_records(trades.tail(args.order_limit))
                    if trades is not None and not trades.empty
                    else [],
                    "signal_adjust": args.signal_adjust,
                    "execution_adjust": args.execution_adjust,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "diagnose-validation-gap":
        result = run_selector_validation_gap(
            cache,
            SelectorValidationGapConfig(
                symbols=symbols,
                start=args.start,
                end=args.end,
                source=args.source,
                signal_adjust=args.signal_adjust,
                execution_adjust=args.execution_adjust,
                cash=args.cash,
                commission_bps=args.commission_bps,
                slippage_bps=args.slippage_bps,
                execution_timing=args.execution_timing,
                hold_days=args.hold_days,
                target_percent_per_position=_normalize_percent(args.target_percent_per_position),
                max_positions=args.max_positions,
                lot_size=args.lot_size,
                take_profit_pct=_normalize_optional_percent(args.take_profit_pct),
                stop_loss_pct=_normalize_optional_percent(args.stop_loss_pct),
                reject_limit_up_buy=not args.allow_limit_up_buy,
                reject_limit_down_sell=not args.allow_limit_down_sell,
                top_n=args.top_n,
                selector=selector,
            ),
            out=Path(args.out) if args.out else None,
        )
        artifacts = result["artifacts"]
        print(
            json.dumps(
                {
                    "summary": result["summary"],
                    "simulator_metrics": result["simulator_metrics"],
                    "backtrader_metrics": result["backtrader_metrics"],
                    "order_comparison": _json_records(artifacts["order_comparison"].head(args.preview_limit)),
                    "equity_comparison": _json_records(artifacts["equity_comparison"].head(args.preview_limit)),
                    "out": args.out,
                    "signal_adjust": args.signal_adjust,
                    "execution_adjust": args.execution_adjust,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "sweep-simulate":
        base_config = SelectionExecutionConfig(
            symbols=symbols,
            start=args.start,
            end=args.end,
            source=args.source,
            signal_adjust=args.signal_adjust,
            execution_adjust=args.execution_adjust,
            cash=args.cash,
            commission_bps=args.commission_bps,
            slippage_bps=args.slippage_bps,
            surge_threshold_pct=_normalize_optional_percent(args.surge_threshold_pct),
            surge_extra_slippage_bps=args.surge_extra_slippage_bps,
            entry_price_field=args.entry_price_field,
            exit_price_field=args.exit_price_field,
            lot_size=args.lot_size,
            reject_limit_up_buy=not args.allow_limit_up_buy,
            reject_limit_down_sell=not args.allow_limit_down_sell,
            top_n=args.top_n,
            selector=selector,
        )
        table = sweep_selection_execution(
            cache,
            base_config,
            hold_days=_parse_int_list(args.hold_days_list, [1]),
            target_percents=[_normalize_percent(item) for item in _parse_float_list(args.target_percent_list, [10])],
            max_positions=_parse_int_list(args.max_positions_list, [1]),
            top_ns=_parse_int_list(args.top_n_list, [args.top_n]),
            stop_losses=_parse_optional_percent_list(args.stop_loss_list),
            take_profits=_parse_optional_percent_list(args.take_profit_list),
            entry_lag_days=_parse_int_list(args.entry_lag_days_list, [0]),
            min_scores=_parse_int_list(args.min_score_list, [args.min_score]),
            rsi_thresholds=_parse_float_list(args.rsi_threshold_list, [args.rsi_threshold]),
            volume_multipliers=_parse_float_list(args.volume_multiplier_list, [args.volume_multiplier]),
            boll_stds=_parse_float_list(args.boll_std_list, [args.boll_std]),
        )
        table = _rank_sweep_table(table, args.rank_by)
        print(
            json.dumps(
                {
                    "rows": _json_records(table.head(args.limit)),
                    "row_count": len(table),
                    "rank_by": args.rank_by,
                    "symbol_count": len(symbols),
                    "signal_adjust": args.signal_adjust,
                    "execution_adjust": args.execution_adjust,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "attribution":
        result = run_selection_hit_rate(
            cache,
            SelectionHitRateConfig(
                symbols=symbols,
                start=args.start,
                end=args.end,
                source=args.source,
                signal_adjust=args.signal_adjust,
                execution_adjust=args.execution_adjust,
                forward_days=args.forward_days,
                top_n=args.top_n,
                price_mode=args.price_mode,
                selector=selector,
            ),
        )
        attribution_tables = summarize_factor_attribution(
            result["evaluated_candidates"],
            min_valid_count=args.min_valid_count,
        )
        print(
            json.dumps(
                {
                    "metrics": result["metrics"],
                    "by_combo": attribution_tables["by_combo"].head(args.limit).to_dict(orient="records"),
                    "by_score": attribution_tables["by_score"].head(args.limit).to_dict(orient="records"),
                    "by_factor": attribution_tables["by_factor"].head(args.limit).to_dict(orient="records"),
                    "symbol_count": len(symbols),
                    "signal_adjust": args.signal_adjust,
                    "execution_adjust": args.execution_adjust,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "sweep-hit-rate":
        base_config = SelectionHitRateConfig(
            symbols=symbols,
            start=args.start,
            end=args.end,
            source=args.source,
            signal_adjust=args.signal_adjust,
            execution_adjust=args.execution_adjust,
            forward_days=args.forward_days,
            top_n=args.top_n,
            price_mode=args.price_mode,
            selector=selector,
        )
        table = sweep_selection_hit_rate(
            cache,
            base_config,
            top_ns=_parse_int_list(args.top_n_list, [args.top_n]),
            min_scores=_parse_int_list(args.min_score_list, [args.min_score]),
            rsi_thresholds=_parse_float_list(args.rsi_threshold_list, [args.rsi_threshold]),
            volume_multipliers=_parse_float_list(args.volume_multiplier_list, [args.volume_multiplier]),
        )
        print(
            json.dumps(
                {
                    "rows": _json_records(table.head(args.limit)),
                    "row_count": len(table),
                    "symbol_count": len(symbols),
                    "signal_adjust": args.signal_adjust,
                    "execution_adjust": args.execution_adjust,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    result = run_selection_backtest(
        cache,
        SelectionBacktestConfig(
            symbols=symbols,
            start=args.start,
            end=args.end,
            source=args.source,
            signal_adjust=args.signal_adjust,
            execution_adjust=args.execution_adjust,
            cash=args.cash,
            commission_bps=args.commission_bps,
            slippage_bps=args.slippage_bps,
            hold_days=args.hold_days,
            entry_lag_days=args.entry_lag_days,
            target_percent_per_position=_normalize_percent(args.target_percent_per_position),
            top_n=args.top_n,
            selector=selector,
        ),
    )
    candidates_df = result["candidates"]
    print(
        json.dumps(
            {
                "metrics": result["metrics"],
                "candidate_count": len(candidates_df),
                "preview_candidates": candidates_df[_candidate_columns(candidates_df)].head(args.top_n).to_dict(
                    orient="records"
                ),
                "signal_adjust": args.signal_adjust,
                "execution_adjust": args.execution_adjust,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", default=SOURCE_BAOSTOCK)
    parser.add_argument("--symbols", default="")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--signal-adjust", default="qfq", choices=["raw", "qfq", "hfq"])
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--min-score", type=int, default=2)
    parser.add_argument("--ma-short", type=int, default=20)
    parser.add_argument("--ma-long", type=int, default=60)
    parser.add_argument("--kdj-window", type=int, default=9)
    parser.add_argument("--macd-fast", type=int, default=12)
    parser.add_argument("--macd-slow", type=int, default=26)
    parser.add_argument("--macd-signal", type=int, default=9)
    parser.add_argument("--rsi-window", type=int, default=14)
    parser.add_argument("--rsi-threshold", type=float, default=55.0)
    parser.add_argument("--volume-window", type=int, default=20)
    parser.add_argument("--volume-multiplier", type=float, default=1.5)
    parser.add_argument("--boll-window", type=int, default=20)
    parser.add_argument("--boll-std", type=float, default=2.0)
    parser.add_argument("--require-factors", default="")
    parser.add_argument("--exclude-factors", default="")


def _selector_config(args: argparse.Namespace) -> FactorSelectorConfig:
    return FactorSelectorConfig(
        ma_short=args.ma_short,
        ma_long=args.ma_long,
        kdj_window=args.kdj_window,
        macd_fast=args.macd_fast,
        macd_slow=args.macd_slow,
        macd_signal=args.macd_signal,
        rsi_window=args.rsi_window,
        rsi_threshold=args.rsi_threshold,
        volume_window=args.volume_window,
        volume_multiplier=args.volume_multiplier,
        boll_window=args.boll_window,
        boll_std=args.boll_std,
        min_score=args.min_score,
        top_n=args.top_n,
        require_factors=tuple(_parse_str_list(args.require_factors)),
        exclude_factors=tuple(_parse_str_list(args.exclude_factors)),
    )


def _symbols(args: argparse.Namespace, cache: ParquetCache) -> list[str]:
    if args.symbols:
        return [item.strip().upper() for item in args.symbols.split(",") if item.strip()]
    return cache.available_symbols(source=args.source, adjust=args.signal_adjust)


def _candidate_columns(frame) -> list[str]:
    columns = [
        "date",
        "symbol",
        "close",
        "factor_score",
        "factor_reasons",
        "ma_breakout",
        "kdj_golden_cross",
        "macd_golden_cross",
        "rsi_momentum",
        "volume_breakout",
        "boll_breakout",
        "entry_date",
        "future_date",
        "entry_price",
        "exit_price",
        "forward_return",
        "outcome",
    ]
    return [column for column in columns if column in frame.columns]


def _normalize_percent(number: float) -> float:
    if abs(number) > 1:
        return number / 100
    return number


def _normalize_optional_percent(number: float | None) -> float | None:
    if number is None:
        return None
    return _normalize_percent(number)


def _parse_int_list(value: str, default: list[int]) -> list[int]:
    if not value:
        return default
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _parse_float_list(value: str, default: list[float]) -> list[float]:
    if not value:
        return default
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def _parse_optional_percent_list(value: str) -> list[float | None]:
    if not value:
        return [None]
    parsed: list[float | None] = []
    for item in value.split(","):
        cleaned = item.strip().lower()
        if not cleaned:
            continue
        if cleaned in {"none", "null", "na"}:
            parsed.append(None)
        else:
            parsed.append(_normalize_percent(float(cleaned)))
    return parsed or [None]


def _parse_str_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _rank_sweep_table(table, rank_by: str):
    if table.empty or rank_by not in table.columns:
        return table
    ascending = rank_by == "max_drawdown"
    secondary = [column for column in ["sharpe", "total_return", "trade_win_rate"] if column in table.columns and column != rank_by]
    return table.sort_values([rank_by, *secondary], ascending=[ascending, *([False] * len(secondary))])


def _json_records(frame):
    return frame.astype(object).where(frame.notna(), None).to_dict(orient="records")


if __name__ == "__main__":
    main()
