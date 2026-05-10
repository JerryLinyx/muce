from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from quant_backtest.backtest import (
    BacktraderConfig,
    BacktraderEngine,
    BacktraderRunner,
    VectorbtConfig,
    VectorbtEngine,
    VectorbtRunner,
    get_signal_sma_cross_strategy_class,
    get_three_falling_buy_three_rising_sell_strategy_class,
    get_three_rising_hold_one_day_strategy_class,
)
from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import SOURCE_BAOSTOCK
from quant_backtest.reports.store import write_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="quant-backtest")
    parser.add_argument("--cache-root", default="data/cache/a_share/daily")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sweep = subparsers.add_parser("sweep")
    _add_common_args(sweep)
    sweep.add_argument("--signal-adjust", default="qfq", choices=["raw", "qfq", "hfq"])
    sweep.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    sweep.add_argument(
        "--strategy",
        default="sma-cross",
        choices=[
            "sma-cross",
            "three-rising-hold-one",
            "three-falling-buy-three-rising-sell",
        ],
    )
    sweep.add_argument("--cash", type=float, default=1_000_000)
    sweep.add_argument("--commission-bps", type=float, default=3.0)
    sweep.add_argument("--slippage-bps", type=float, default=5.0)
    sweep.add_argument("--size-granularity", type=float, default=1.0)
    sweep.add_argument("--fast-periods", default="5")
    sweep.add_argument("--slow-periods", default="20")
    sweep.add_argument("--signal-counts", default="3")
    sweep.add_argument("--hold-bars-list", default="1")
    sweep.add_argument("--max-hold-days-list", default="none")
    sweep.add_argument("--stop-losses", default="none")
    sweep.add_argument("--take-profits", default="none")
    sweep.add_argument("--target-percents", default="")
    sweep.add_argument("--target-percent", type=float, default=0.95)
    sweep.add_argument("--pyramiding", action="store_true")
    sweep.add_argument("--max-position-percents", default="")
    sweep.add_argument("--max-position-percent", type=float, default=1.0)
    sweep.add_argument("--rank-by", default="total_return")
    sweep.add_argument("--top", type=int, default=20)
    sweep.add_argument("--no-report", action="store_true",
                       help="Do not write the run to reports/sweeps/")
    sweep.add_argument("--reports-dir", default="reports",
                       help="Directory under which to write run artifacts")

    validate = subparsers.add_parser("validate")
    _add_common_args(validate)
    validate.add_argument("--signal-adjust", default="qfq", choices=["raw", "qfq", "hfq"])
    validate.add_argument("--execution-adjust", default="raw", choices=["raw", "qfq", "hfq"])
    validate.add_argument("--execution-timing", default="next_open", choices=["next_open", "same_close"])
    validate.add_argument("--cash", type=float, default=1_000_000)
    validate.add_argument("--commission-bps", type=float, default=3.0)
    validate.add_argument("--slippage-bps", type=float, default=5.0)
    validate.add_argument("--fast-period", type=int, default=5)
    validate.add_argument("--slow-period", type=int, default=20)
    validate.add_argument(
        "--strategy",
        default="sma-cross",
        choices=[
            "sma-cross",
            "three-rising-hold-one",
            "three-falling-buy-three-rising-sell",
        ],
    )
    validate.add_argument("--target-percent", type=float, default=0.95)
    validate.add_argument("--hold-bars", type=int, default=1)
    validate.add_argument("--signal-count", type=int, default=3)
    validate.add_argument("--no-report", action="store_true",
                          help="Do not write the run to reports/validations/")
    validate.add_argument("--reports-dir", default="reports",
                          help="Directory under which to write run artifacts")

    args = parser.parse_args()
    cache = ParquetCache(Path(args.cache_root))
    symbols = [item.strip().upper() for item in args.symbols.split(",") if item.strip()]

    if args.command == "sweep":
        config = VectorbtConfig(
            symbols=symbols,
            strategy=args.strategy,
            start=args.start,
            end=args.end,
            cash=args.cash,
            commission_bps=args.commission_bps,
            slippage_bps=args.slippage_bps,
            size_granularity=args.size_granularity,
            source=args.source,
            signal_adjust=args.signal_adjust,
            execution_adjust=args.execution_adjust,
            strategy_kwargs={
                "target_percent": args.target_percent,
                "pyramiding": args.pyramiding,
                "max_position_percent": _normalize_percent(args.max_position_percent),
            },
        )
        started = time.perf_counter()
        result = VectorbtEngine(cache).sweep(config, _sweep_grid(args))
        elapsed = time.perf_counter() - started
        ranked = result.ranked(args.rank_by).head(args.top)
        print(
            json.dumps(
                {
                    "metrics": ranked.to_dict(orient="records"),
                    "row_count": len(result.metrics),
                    "strategy": args.strategy,
                    "signal_adjust": args.signal_adjust,
                    "execution_adjust": args.execution_adjust,
                    "rank_by": args.rank_by,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if not args.no_report:
            close = result.close
            data_start, data_end = _index_date_range(close, args.start, args.end)
            write_report(
                kind="sweep",
                config=_sweep_config_dict(args),
                manifest_extra={
                    "elapsed_seconds": elapsed,
                    "data_range": {"start": data_start, "end": data_end},
                    "symbols": list(symbols),
                    "strategy": args.strategy,
                    "grid_size": int(len(result.metrics)),
                    "rank_by": args.rank_by,
                    "top_combos": ranked.head(5).to_dict(orient="records"),
                },
                artifacts={"results": result.metrics},
                base_dir=Path(args.reports_dir),
            )
        return

    if args.command == "validate":
        config = BacktraderConfig(
            symbols=symbols,
            start=args.start,
            end=args.end,
            cash=args.cash,
            commission_bps=args.commission_bps,
            slippage_bps=args.slippage_bps,
            source=args.source,
            signal_adjust=args.signal_adjust,
            execution_adjust=args.execution_adjust,
            execution_timing=args.execution_timing,
            strategy_kwargs=_strategy_kwargs(args),
        )
        started = time.perf_counter()
        result = BacktraderEngine(cache).run(_strategy_class(args.strategy), config)
        elapsed = time.perf_counter() - started
        print(
            json.dumps(
                {
                    "metrics": result.metrics,
                    "equity_rows": len(result.equity_curve),
                    "order_rows": len(result.orders),
                    "trade_rows": len(result.trades),
                    "signal_adjust": args.signal_adjust,
                    "execution_adjust": args.execution_adjust,
                    "execution_timing": args.execution_timing,
                    "strategy": args.strategy,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if not args.no_report:
            equity_df = result.equity_curve
            data_start, data_end = _frame_date_range(equity_df, args.start, args.end)
            write_report(
                kind="validate",
                config=_validate_config_dict(args),
                manifest_extra={
                    "elapsed_seconds": elapsed,
                    "data_range": {"start": data_start, "end": data_end},
                    "symbols": list(symbols),
                    "strategy": args.strategy,
                    "signal_adjust": args.signal_adjust,
                    "execution_adjust": args.execution_adjust,
                    "summary_metrics": dict(result.metrics),
                },
                artifacts={"equity": equity_df, "trades": result.trades, "orders": result.orders},
                base_dir=Path(args.reports_dir),
            )


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", default=SOURCE_BAOSTOCK)
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")


def _panel_summary(panels: dict) -> dict[str, dict[str, object]]:
    summary = {}
    for field, frame in panels.items():
        summary[field] = {
            "rows": int(frame.shape[0]),
            "columns": list(frame.columns.astype(str)) if hasattr(frame, "columns") else [],
            "start": frame.index.min().date().isoformat() if not frame.empty else None,
            "end": frame.index.max().date().isoformat() if not frame.empty else None,
        }
    return summary


def _sweep_grid(args: argparse.Namespace) -> dict[str, list[object]]:
    if args.strategy == "sma-cross":
        return {
            "fast_period": _int_list(args.fast_periods),
            "slow_period": _int_list(args.slow_periods),
            "target_percent": _target_percent_list(args),
        }
    if args.strategy == "three-rising-hold-one":
        grid = {
            "signal_count": _int_list(args.signal_counts),
            "hold_bars": _int_list(args.hold_bars_list),
            "target_percent": _target_percent_list(args),
            "stop_loss": _optional_percent_list(args.stop_losses),
            "take_profit": _optional_percent_list(args.take_profits),
        }
        if args.pyramiding:
            grid["pyramiding"] = [True]
            grid["max_position_percent"] = _max_position_percent_list(args)
        return grid
    if args.strategy == "three-falling-buy-three-rising-sell":
        grid = {
            "signal_count": _int_list(args.signal_counts),
            "target_percent": _target_percent_list(args),
            "max_hold_days": _optional_int_list(args.max_hold_days_list),
            "stop_loss": _optional_percent_list(args.stop_losses),
            "take_profit": _optional_percent_list(args.take_profits),
        }
        if args.pyramiding:
            grid["pyramiding"] = [True]
            grid["max_position_percent"] = _max_position_percent_list(args)
        return grid
    raise ValueError(f"unsupported strategy {args.strategy!r}")


def _int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _optional_int_list(value: str) -> list[int | None]:
    items = []
    for raw in value.split(","):
        item = raw.strip().lower()
        if not item:
            continue
        if item in {"none", "null", "na"}:
            items.append(None)
        else:
            items.append(int(item))
    return items or [None]


def _target_percent_list(args: argparse.Namespace) -> list[float]:
    if args.target_percents:
        return _percent_list(args.target_percents)
    return [_normalize_percent(args.target_percent)]


def _max_position_percent_list(args: argparse.Namespace) -> list[float]:
    if args.max_position_percents:
        return _percent_list(args.max_position_percents)
    return [_normalize_percent(args.max_position_percent)]


def _optional_percent_list(value: str) -> list[float | None]:
    items = []
    for raw in value.split(","):
        item = raw.strip().lower()
        if not item:
            continue
        if item in {"none", "null", "na"}:
            items.append(None)
        else:
            items.append(_parse_percent(item))
    return items or [None]


def _percent_list(value: str) -> list[float]:
    return [_parse_percent(item.strip()) for item in value.split(",") if item.strip()]


def _parse_percent(value: str) -> float:
    if value.endswith("%"):
        return float(value[:-1]) / 100
    return _normalize_percent(float(value))


def _normalize_percent(number: float) -> float:
    if abs(number) > 1:
        return number / 100
    return number


_REPORT_EXCLUDE_KEYS = {"command", "cache_root", "no_report", "reports_dir"}


def _frame_date_range(df, fallback_start: str | None, fallback_end: str | None) -> tuple[str, str]:
    import pandas as pd
    if df is None or df.empty:
        return (fallback_start or "", fallback_end or "")
    if "date" in df.columns:
        ser = pd.to_datetime(df["date"], errors="coerce").dropna()
        if not ser.empty:
            return (ser.min().date().isoformat(), ser.max().date().isoformat())
    return _index_date_range(df, fallback_start, fallback_end)


def _index_date_range(df, fallback_start: str | None, fallback_end: str | None) -> tuple[str, str]:
    import pandas as pd
    if df is None or df.empty:
        return (fallback_start or "", fallback_end or "")
    if isinstance(df.index, pd.DatetimeIndex):
        return (df.index.min().date().isoformat(), df.index.max().date().isoformat())
    return (fallback_start or "", fallback_end or "")


def _sweep_config_dict(args: argparse.Namespace) -> dict:
    payload = {
        key: value
        for key, value in vars(args).items()
        if key not in _REPORT_EXCLUDE_KEYS
    }
    return payload


def _validate_config_dict(args: argparse.Namespace) -> dict:
    return _sweep_config_dict(args)


def _strategy_class(name: str):
    if name == "sma-cross":
        return get_signal_sma_cross_strategy_class()
    if name == "three-rising-hold-one":
        return get_three_rising_hold_one_day_strategy_class()
    if name == "three-falling-buy-three-rising-sell":
        return get_three_falling_buy_three_rising_sell_strategy_class()
    raise ValueError(f"unsupported strategy {name!r}")


def _strategy_kwargs(args: argparse.Namespace) -> dict[str, object]:
    if args.strategy == "sma-cross":
        return {
            "fast_period": args.fast_period,
            "slow_period": args.slow_period,
            "target_percent": args.target_percent,
        }
    if args.strategy == "three-rising-hold-one":
        return {
            "target_percent": args.target_percent,
            "hold_bars": args.hold_bars,
        }
    if args.strategy == "three-falling-buy-three-rising-sell":
        return {
            "target_percent": args.target_percent,
            "signal_count": args.signal_count,
        }
    raise ValueError(f"unsupported strategy {args.strategy!r}")


if __name__ == "__main__":
    main()
