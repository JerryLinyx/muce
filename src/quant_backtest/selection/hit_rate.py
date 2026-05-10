from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from typing import Any, Literal

import pandas as pd

from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import Adjust, SOURCE_BAOSTOCK
from quant_backtest.selection.factors import FACTOR_COLUMNS, FactorSelectorConfig, build_factor_table, select_candidates

PriceMode = Literal["close_to_next_close", "next_open_to_next_close"]


@dataclass(frozen=True)
class SelectionHitRateConfig:
    symbols: list[str]
    start: str | None = None
    end: str | None = None
    source: str = SOURCE_BAOSTOCK
    signal_adjust: Adjust = "qfq"
    execution_adjust: Adjust = "raw"
    forward_days: int = 1
    top_n: int = 10
    price_mode: PriceMode = "close_to_next_close"
    selector: FactorSelectorConfig = FactorSelectorConfig(top_n=10)


def run_selection_hit_rate(cache: ParquetCache, config: SelectionHitRateConfig) -> dict[str, Any]:
    if config.forward_days < 1:
        raise ValueError("forward_days must be >= 1")
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
    evaluated = evaluate_candidate_hit_rate(
        candidates,
        execution_data,
        forward_days=config.forward_days,
        price_mode=config.price_mode,
    )
    daily_summary = summarize_daily_hit_rate(evaluated)
    metrics = summarize_overall_hit_rate(evaluated, daily_summary)
    metrics.update(
        {
            "top_n": int(config.top_n),
            "min_score": int(config.selector.min_score),
            "forward_days": int(config.forward_days),
            "price_mode": config.price_mode,
            "signal_adjust": config.signal_adjust,
            "execution_adjust": config.execution_adjust,
        }
    )
    return {
        "metrics": metrics,
        "factor_table": factor_table,
        "candidates": candidates,
        "evaluated_candidates": evaluated,
        "daily_summary": daily_summary,
    }


def sweep_selection_hit_rate(
    cache: ParquetCache,
    base_config: SelectionHitRateConfig,
    *,
    top_ns: list[int],
    min_scores: list[int],
    rsi_thresholds: list[float],
    volume_multipliers: list[float],
) -> pd.DataFrame:
    signal_data = cache.read_many(
        source=base_config.source,
        adjust=base_config.signal_adjust,
        symbols=base_config.symbols,
        start=base_config.start,
        end=base_config.end,
    )
    execution_data = cache.read_many(
        source=base_config.source,
        adjust=base_config.execution_adjust,
        symbols=base_config.symbols,
        start=base_config.start,
        end=base_config.end,
    )
    rows: list[dict[str, Any]] = []
    for rsi_threshold, volume_multiplier in product(rsi_thresholds, volume_multipliers):
        selector = replace(
            base_config.selector,
            rsi_threshold=rsi_threshold,
            volume_multiplier=volume_multiplier,
            min_score=min(min_scores),
            top_n=max(top_ns),
        )
        factor_table = build_factor_table(signal_data, selector)
        for top_n, min_score in product(top_ns, min_scores):
            candidates = _select_with_min_score(factor_table, min_score=min_score, top_n=top_n)
            evaluated = evaluate_candidate_hit_rate(
                candidates,
                execution_data,
                forward_days=base_config.forward_days,
                price_mode=base_config.price_mode,
            )
            daily_summary = summarize_daily_hit_rate(evaluated)
            metrics = summarize_overall_hit_rate(evaluated, daily_summary)
            metrics.update(
                {
                    "top_n": int(top_n),
                    "min_score": int(min_score),
                    "forward_days": int(base_config.forward_days),
                    "price_mode": base_config.price_mode,
                    "signal_adjust": base_config.signal_adjust,
                    "execution_adjust": base_config.execution_adjust,
                }
            )
            rows.append(
                {
                    "top_n": top_n,
                    "min_score": min_score,
                    "rsi_threshold": rsi_threshold,
                    "volume_multiplier": volume_multiplier,
                    **metrics,
                }
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["win_rate", "avg_forward_return", "valid_signals"],
        ascending=[False, False, False],
    )


def _select_with_min_score(factor_table: pd.DataFrame, *, min_score: int, top_n: int) -> pd.DataFrame:
    data = factor_table.copy()
    base_selected = data["selected"] if "selected" in data.columns else data["tradable"]
    data["selected"] = base_selected & data["factor_score"].ge(min_score)
    return select_candidates(data, top_n=top_n)


def evaluate_candidate_hit_rate(
    candidates: pd.DataFrame,
    execution_data: pd.DataFrame,
    *,
    forward_days: int = 1,
    price_mode: PriceMode = "close_to_next_close",
) -> pd.DataFrame:
    if forward_days < 1:
        raise ValueError("forward_days must be >= 1")
    if price_mode not in ("close_to_next_close", "next_open_to_next_close"):
        raise ValueError(f"unsupported price_mode: {price_mode}")

    if candidates.empty:
        return _empty_evaluated_candidates()
    _validate_execution_data(execution_data)

    selected = candidates.copy()
    selected["date"] = pd.to_datetime(selected["date"])
    execution = execution_data.copy()
    execution["date"] = pd.to_datetime(execution["date"])
    close = execution.pivot(index="date", columns="symbol", values="close").sort_index()
    open_ = execution.pivot(index="date", columns="symbol", values="open").sort_index()
    trading_dates = list(close.index)
    future_date_by_signal = {
        date: trading_dates[index + forward_days]
        for index, date in enumerate(trading_dates)
        if index + forward_days < len(trading_dates)
    }
    next_date_by_signal = {
        date: trading_dates[index + 1]
        for index, date in enumerate(trading_dates)
        if index + 1 < len(trading_dates)
    }

    rows: list[dict[str, Any]] = []
    for row in selected.itertuples(index=False):
        signal_date = row.date
        symbol = row.symbol
        future_date = future_date_by_signal.get(signal_date)
        entry_date = signal_date if price_mode == "close_to_next_close" else next_date_by_signal.get(signal_date)
        if future_date is None or entry_date is None or symbol not in close.columns:
            rows.append(_evaluated_row(row, entry_date, future_date, None, None, None, "invalid"))
            continue
        if price_mode == "close_to_next_close":
            entry_price = _lookup_price(close, signal_date, symbol)
        else:
            entry_price = _lookup_price(open_, entry_date, symbol)
        exit_price = _lookup_price(close, future_date, symbol)
        if entry_price is None or exit_price is None or entry_price <= 0 or exit_price <= 0:
            rows.append(_evaluated_row(row, entry_date, future_date, entry_price, exit_price, None, "invalid"))
            continue
        forward_return = exit_price / entry_price - 1
        if forward_return > 0:
            outcome = "win"
        elif forward_return < 0:
            outcome = "loss"
        else:
            outcome = "flat"
        rows.append(_evaluated_row(row, entry_date, future_date, entry_price, exit_price, forward_return, outcome))

    evaluated = pd.DataFrame(rows)
    evaluated["date"] = pd.to_datetime(evaluated["date"])
    evaluated["entry_date"] = pd.to_datetime(evaluated["entry_date"])
    evaluated["future_date"] = pd.to_datetime(evaluated["future_date"])
    evaluated["is_valid"] = evaluated["outcome"].ne("invalid")
    evaluated["is_win"] = evaluated["outcome"].eq("win")
    evaluated["is_loss"] = evaluated["outcome"].eq("loss")
    evaluated["is_flat"] = evaluated["outcome"].eq("flat")
    return evaluated.sort_values(["date", "factor_score", "symbol"], ascending=[True, False, True]).reset_index(
        drop=True
    )


def summarize_daily_hit_rate(evaluated: pd.DataFrame) -> pd.DataFrame:
    if evaluated.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "signal_count",
                "valid_count",
                "win_count",
                "loss_count",
                "flat_count",
                "invalid_count",
                "win_rate",
                "avg_forward_return",
                "median_forward_return",
            ]
        )
    grouped = evaluated.groupby("date", sort=True)
    summary = grouped.agg(
        signal_count=("symbol", "size"),
        valid_count=("is_valid", "sum"),
        win_count=("is_win", "sum"),
        loss_count=("is_loss", "sum"),
        flat_count=("is_flat", "sum"),
        avg_forward_return=("forward_return", "mean"),
        median_forward_return=("forward_return", "median"),
    ).reset_index()
    summary["invalid_count"] = summary["signal_count"] - summary["valid_count"]
    summary["win_rate"] = summary["win_count"] / summary["valid_count"].replace(0, pd.NA)
    columns = [
        "date",
        "signal_count",
        "valid_count",
        "win_count",
        "loss_count",
        "flat_count",
        "invalid_count",
        "win_rate",
        "avg_forward_return",
        "median_forward_return",
    ]
    return summary[columns]


def summarize_overall_hit_rate(evaluated: pd.DataFrame, daily_summary: pd.DataFrame | None = None) -> dict[str, Any]:
    if daily_summary is None:
        daily_summary = summarize_daily_hit_rate(evaluated)
    if evaluated.empty:
        return {
            "signal_days": 0,
            "total_signals": 0,
            "valid_signals": 0,
            "invalid_signals": 0,
            "win_count": 0,
            "loss_count": 0,
            "flat_count": 0,
            "win_rate": None,
            "avg_daily_win_rate": None,
            "positive_day_count": 0,
            "positive_day_rate": None,
            "avg_forward_return": None,
            "median_forward_return": None,
        }
    valid = evaluated[evaluated["is_valid"]]
    total = int(len(evaluated))
    valid_count = int(len(valid))
    win_count = int(evaluated["is_win"].sum())
    loss_count = int(evaluated["is_loss"].sum())
    flat_count = int(evaluated["is_flat"].sum())
    positive_day_count = int(daily_summary["avg_forward_return"].gt(0).sum()) if not daily_summary.empty else 0
    signal_days = int(evaluated["date"].nunique())
    return {
        "signal_days": signal_days,
        "total_signals": total,
        "valid_signals": valid_count,
        "invalid_signals": total - valid_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "flat_count": flat_count,
        "win_rate": win_count / valid_count if valid_count else None,
        "avg_daily_win_rate": daily_summary["win_rate"].dropna().mean() if not daily_summary.empty else None,
        "positive_day_count": positive_day_count,
        "positive_day_rate": positive_day_count / signal_days if signal_days else None,
        "avg_forward_return": valid["forward_return"].mean() if valid_count else None,
        "median_forward_return": valid["forward_return"].median() if valid_count else None,
    }


def summarize_factor_attribution(evaluated: pd.DataFrame, *, min_valid_count: int = 30) -> dict[str, pd.DataFrame]:
    valid = evaluated[evaluated["is_valid"]].copy() if not evaluated.empty else evaluated.copy()
    if valid.empty:
        empty = pd.DataFrame()
        return {"by_combo": empty, "by_score": empty, "by_factor": empty}
    return {
        "by_combo": _summarize_group(valid, ["factor_reasons"], min_valid_count=min_valid_count),
        "by_score": _summarize_group(valid, ["factor_score"], min_valid_count=min_valid_count),
        "by_factor": _summarize_individual_factors(valid, min_valid_count=min_valid_count),
    }


def _empty_evaluated_candidates() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "symbol",
            "entry_date",
            "future_date",
            "entry_price",
            "exit_price",
            "forward_return",
            "outcome",
            "is_valid",
            "is_win",
            "is_loss",
            "is_flat",
        ]
    )


def _summarize_group(data: pd.DataFrame, group_columns: list[str], *, min_valid_count: int) -> pd.DataFrame:
    grouped = data.groupby(group_columns, dropna=False, sort=False)
    summary = grouped.agg(
        valid_count=("symbol", "size"),
        signal_days=("date", "nunique"),
        win_count=("is_win", "sum"),
        loss_count=("is_loss", "sum"),
        flat_count=("is_flat", "sum"),
        avg_forward_return=("forward_return", "mean"),
        median_forward_return=("forward_return", "median"),
    ).reset_index()
    summary = summary[summary["valid_count"].ge(min_valid_count)].copy()
    if summary.empty:
        return summary
    summary["win_rate"] = summary["win_count"] / summary["valid_count"]
    return summary.sort_values(
        ["win_rate", "median_forward_return", "avg_forward_return", "valid_count"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)


def _summarize_individual_factors(data: pd.DataFrame, *, min_valid_count: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for factor in FACTOR_COLUMNS:
        subset = data[data[factor]]
        if len(subset) < min_valid_count:
            continue
        rows.append(
            {
                "factor": factor,
                "valid_count": int(len(subset)),
                "signal_days": int(subset["date"].nunique()),
                "win_count": int(subset["is_win"].sum()),
                "loss_count": int(subset["is_loss"].sum()),
                "flat_count": int(subset["is_flat"].sum()),
                "win_rate": float(subset["is_win"].sum() / len(subset)),
                "avg_forward_return": float(subset["forward_return"].mean()),
                "median_forward_return": float(subset["forward_return"].median()),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["win_rate", "median_forward_return", "avg_forward_return", "valid_count"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)


def _validate_execution_data(execution_data: pd.DataFrame) -> None:
    required = {"date", "symbol", "open", "close"}
    missing = required.difference(execution_data.columns)
    if missing:
        raise KeyError(f"missing required execution columns: {sorted(missing)}")


def _lookup_price(prices: pd.DataFrame, date: pd.Timestamp, symbol: str) -> float | None:
    if date not in prices.index or symbol not in prices.columns:
        return None
    value = prices.loc[date, symbol]
    if pd.isna(value):
        return None
    return float(value)


def _evaluated_row(
    row: Any,
    entry_date: pd.Timestamp | None,
    future_date: pd.Timestamp | None,
    entry_price: float | None,
    exit_price: float | None,
    forward_return: float | None,
    outcome: str,
) -> dict[str, Any]:
    base = row._asdict()
    base.update(
        {
            "entry_date": entry_date,
            "future_date": future_date,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "forward_return": forward_return,
            "outcome": outcome,
        }
    )
    return base
