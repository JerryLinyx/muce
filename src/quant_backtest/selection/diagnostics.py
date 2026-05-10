from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import Adjust, SOURCE_BAOSTOCK
from quant_backtest.selection.backtrader_validation import (
    SelectorBacktraderValidationConfig,
    run_selector_backtrader_validation,
)
from quant_backtest.selection.execution import SelectionExecutionConfig, run_selection_execution_simulation
from quant_backtest.selection.factors import FactorSelectorConfig

ExecutionTiming = Literal["same_close", "next_open"]


@dataclass(frozen=True)
class SelectorValidationGapConfig:
    symbols: list[str]
    start: str | None = None
    end: str | None = None
    source: str = SOURCE_BAOSTOCK
    signal_adjust: Adjust = "qfq"
    execution_adjust: Adjust = "raw"
    cash: float = 1_000_000.0
    commission_bps: float = 3.0
    slippage_bps: float = 5.0
    execution_timing: ExecutionTiming = "same_close"
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
    equity_abs_tolerance: float = 1e-6
    price_abs_tolerance: float = 1e-6
    share_abs_tolerance: float = 1e-6


def run_selector_validation_gap(
    cache: ParquetCache,
    config: SelectorValidationGapConfig,
    *,
    out: Path | None = None,
) -> dict[str, Any]:
    simulator_result = run_selection_execution_simulation(cache, _simulation_config(config))
    backtrader_result = run_selector_backtrader_validation(cache, _backtrader_config(config))
    bt_payload = backtrader_result["result"]

    simulator_orders = normalize_simulator_orders(simulator_result["orders"])
    backtrader_orders = normalize_backtrader_orders(bt_payload.orders if bt_payload is not None else pd.DataFrame())
    simulator_equity = normalize_simulator_equity(simulator_result["equity"])
    backtrader_equity = normalize_backtrader_equity(
        bt_payload.equity_curve if bt_payload is not None else pd.DataFrame()
    )

    order_comparison = compare_order_summaries(
        simulator_orders,
        backtrader_orders,
        price_abs_tolerance=config.price_abs_tolerance,
        share_abs_tolerance=config.share_abs_tolerance,
    )
    equity_comparison = compare_equity_curves(
        simulator_equity,
        backtrader_equity,
        abs_tolerance=config.equity_abs_tolerance,
    )
    summary = _build_gap_summary(
        simulator_metrics=simulator_result["metrics"],
        backtrader_metrics=backtrader_result["metrics"],
        simulator_orders=simulator_orders,
        backtrader_orders=backtrader_orders,
        order_comparison=order_comparison,
        equity_comparison=equity_comparison,
    )

    artifacts = {
        "simulator_orders": simulator_orders,
        "backtrader_orders": backtrader_orders,
        "simulator_equity": simulator_equity,
        "backtrader_equity": backtrader_equity,
        "order_comparison": order_comparison,
        "equity_comparison": equity_comparison,
        "candidates": simulator_result["candidates"],
    }
    if out is not None:
        _export_gap_artifacts(out, summary, artifacts)

    return {
        "summary": summary,
        "simulator_metrics": simulator_result["metrics"],
        "backtrader_metrics": backtrader_result["metrics"],
        "artifacts": artifacts,
    }


def normalize_simulator_orders(orders: pd.DataFrame) -> pd.DataFrame:
    columns = ["date", "symbol", "side", "status", "reason", "shares", "price", "commission"]
    if orders.empty:
        return pd.DataFrame(columns=columns)
    data = orders.copy()
    data["date"] = pd.to_datetime(data["date"]).dt.date.astype(str)
    data["status"] = data["status"].map({"filled": "filled", "rejected": "rejected"}).fillna(data["status"])
    data["reason"] = data.get("reason", "").fillna("")
    data["shares"] = pd.to_numeric(data.get("shares", 0), errors="coerce").fillna(0.0).abs()
    data["price"] = pd.to_numeric(data.get("fill_price"), errors="coerce")
    data["commission"] = pd.to_numeric(data.get("commission", 0), errors="coerce").fillna(0.0)
    return data[columns].sort_values(["date", "symbol", "side", "status"]).reset_index(drop=True)


def normalize_backtrader_orders(orders: pd.DataFrame) -> pd.DataFrame:
    columns = ["date", "symbol", "side", "status", "reason", "shares", "price", "commission"]
    if orders.empty:
        return pd.DataFrame(columns=columns)
    data = orders.copy()
    data["date"] = pd.to_datetime(data["date"]).dt.date.astype(str)
    data["status"] = data["status"].map(
        {
            "Completed": "filled",
            "Margin": "rejected",
            "Rejected": "rejected",
            "Canceled": "rejected",
            "Submitted": "submitted",
            "Accepted": "accepted",
        }
    ).fillna(data["status"])
    data["reason"] = data["status"]
    data["shares"] = pd.to_numeric(data.get("executed_size", 0), errors="coerce").fillna(0.0).abs()
    data["price"] = pd.to_numeric(data.get("executed_price", 0), errors="coerce").replace(0, pd.NA)
    data["commission"] = pd.to_numeric(data.get("commission", 0), errors="coerce").fillna(0.0)
    return data[columns].sort_values(["date", "symbol", "side", "status"]).reset_index(drop=True)


def normalize_simulator_equity(equity: pd.DataFrame) -> pd.DataFrame:
    if equity.empty:
        return pd.DataFrame(columns=["date", "value", "cash"])
    data = equity.reset_index().copy()
    data["date"] = pd.to_datetime(data["date"]).dt.date.astype(str)
    return data[["date", "value", "cash"]].sort_values("date").reset_index(drop=True)


def normalize_backtrader_equity(equity: pd.DataFrame) -> pd.DataFrame:
    if equity.empty:
        return pd.DataFrame(columns=["date", "value", "cash"])
    data = equity.copy()
    data["date"] = pd.to_datetime(data["date"]).dt.date.astype(str)
    return data[["date", "value", "cash"]].sort_values("date").reset_index(drop=True)


def compare_order_summaries(
    simulator_orders: pd.DataFrame,
    backtrader_orders: pd.DataFrame,
    *,
    price_abs_tolerance: float,
    share_abs_tolerance: float,
) -> pd.DataFrame:
    simulator = _filled_order_summary(simulator_orders, "simulator")
    backtrader = _filled_order_summary(backtrader_orders, "backtrader")
    merged = simulator.merge(backtrader, how="outer", on=["date", "symbol", "side"])
    if merged.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "symbol",
                "side",
                "category",
                "simulator_shares",
                "backtrader_shares",
                "simulator_price",
                "backtrader_price",
            ]
        )

    for column in [
        "simulator_shares",
        "backtrader_shares",
        "simulator_commission",
        "backtrader_commission",
    ]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0.0)
    merged["share_diff"] = merged["simulator_shares"] - merged["backtrader_shares"]
    merged["price_diff"] = merged["simulator_price"] - merged["backtrader_price"]
    merged["commission_diff"] = merged["simulator_commission"] - merged["backtrader_commission"]
    merged["category"] = merged.apply(
        lambda row: _order_diff_category(
            row,
            price_abs_tolerance=price_abs_tolerance,
            share_abs_tolerance=share_abs_tolerance,
        ),
        axis=1,
    )
    mismatched = merged[merged["category"].ne("matched")].copy()
    return mismatched.sort_values(["date", "symbol", "side"]).reset_index(drop=True)


def compare_equity_curves(
    simulator_equity: pd.DataFrame,
    backtrader_equity: pd.DataFrame,
    *,
    abs_tolerance: float,
) -> pd.DataFrame:
    merged = simulator_equity.merge(backtrader_equity, how="outer", on="date", suffixes=("_simulator", "_backtrader"))
    if merged.empty:
        return pd.DataFrame(columns=["date", "value_diff", "cash_diff", "category"])
    merged = merged.sort_values("date").reset_index(drop=True)
    merged["value_diff"] = merged["value_simulator"] - merged["value_backtrader"]
    merged["cash_diff"] = merged["cash_simulator"] - merged["cash_backtrader"]
    missing = merged[["value_simulator", "value_backtrader"]].isna().any(axis=1)
    value_diff = merged["value_diff"].abs().gt(abs_tolerance)
    cash_diff = merged["cash_diff"].abs().gt(abs_tolerance)
    merged["category"] = "matched"
    merged.loc[missing, "category"] = "missing_date"
    merged.loc[~missing & value_diff & cash_diff, "category"] = "value_and_cash"
    merged.loc[~missing & value_diff & ~cash_diff, "category"] = "value"
    merged.loc[~missing & ~value_diff & cash_diff, "category"] = "cash"
    return merged[merged["category"].ne("matched")].reset_index(drop=True)


def _simulation_config(config: SelectorValidationGapConfig) -> SelectionExecutionConfig:
    if config.execution_timing == "same_close":
        entry_lag_days = 0
        entry_price_field = "close"
    else:
        entry_lag_days = 1
        entry_price_field = "open"
    return SelectionExecutionConfig(
        symbols=config.symbols,
        start=config.start,
        end=config.end,
        source=config.source,
        signal_adjust=config.signal_adjust,
        execution_adjust=config.execution_adjust,
        cash=config.cash,
        commission_bps=config.commission_bps,
        slippage_bps=config.slippage_bps,
        surge_threshold_pct=None,
        hold_days=config.hold_days,
        entry_lag_days=entry_lag_days,
        entry_price_field=entry_price_field,  # type: ignore[arg-type]
        exit_price_field="close",
        target_percent_per_position=config.target_percent_per_position,
        max_positions=config.max_positions,
        lot_size=config.lot_size,
        reject_limit_up_buy=config.reject_limit_up_buy,
        reject_limit_down_sell=config.reject_limit_down_sell,
        take_profit_pct=config.take_profit_pct,
        stop_loss_pct=config.stop_loss_pct,
        top_n=config.top_n,
        selector=config.selector,
    )


def _backtrader_config(config: SelectorValidationGapConfig) -> SelectorBacktraderValidationConfig:
    return SelectorBacktraderValidationConfig(
        symbols=config.symbols,
        start=config.start,
        end=config.end,
        source=config.source,
        signal_adjust=config.signal_adjust,
        execution_adjust=config.execution_adjust,
        cash=config.cash,
        commission_bps=config.commission_bps,
        slippage_bps=config.slippage_bps,
        execution_timing=config.execution_timing,
        hold_days=config.hold_days,
        target_percent_per_position=config.target_percent_per_position,
        max_positions=config.max_positions,
        lot_size=config.lot_size,
        take_profit_pct=config.take_profit_pct,
        stop_loss_pct=config.stop_loss_pct,
        reject_limit_up_buy=config.reject_limit_up_buy,
        reject_limit_down_sell=config.reject_limit_down_sell,
        top_n=config.top_n,
        selector=config.selector,
    )


def _filled_order_summary(orders: pd.DataFrame, prefix: str) -> pd.DataFrame:
    columns = ["date", "symbol", "side", f"{prefix}_shares", f"{prefix}_price", f"{prefix}_commission"]
    if orders.empty:
        return pd.DataFrame(columns=columns)
    data = orders[orders["status"].eq("filled")].copy()
    if data.empty:
        return pd.DataFrame(columns=columns)

    def weighted_price(group: pd.DataFrame) -> float | None:
        shares = group["shares"].sum()
        if shares <= 0:
            return None
        return float((group["price"] * group["shares"]).sum() / shares)

    grouped = data.groupby(["date", "symbol", "side"], sort=False)
    rows = grouped.agg(
        **{
            f"{prefix}_shares": ("shares", "sum"),
            f"{prefix}_commission": ("commission", "sum"),
        }
    ).reset_index()
    prices = grouped.apply(weighted_price, include_groups=False).reset_index(name=f"{prefix}_price")
    return rows.merge(prices, on=["date", "symbol", "side"], how="left")[columns]


def _order_diff_category(row: pd.Series, *, price_abs_tolerance: float, share_abs_tolerance: float) -> str:
    simulator_missing = row["simulator_shares"] == 0
    backtrader_missing = row["backtrader_shares"] == 0
    if simulator_missing and not backtrader_missing:
        return "missing_in_simulator"
    if backtrader_missing and not simulator_missing:
        return "missing_in_backtrader"
    share_diff = abs(float(row["share_diff"])) > share_abs_tolerance
    price_diff = pd.notna(row["price_diff"]) and abs(float(row["price_diff"])) > price_abs_tolerance
    if share_diff and price_diff:
        return "sizing_and_fill_price"
    if share_diff:
        return "sizing"
    if price_diff:
        return "fill_price"
    if abs(float(row["commission_diff"])) > price_abs_tolerance:
        return "commission"
    return "matched"


def _build_gap_summary(
    *,
    simulator_metrics: dict[str, Any],
    backtrader_metrics: dict[str, Any],
    simulator_orders: pd.DataFrame,
    backtrader_orders: pd.DataFrame,
    order_comparison: pd.DataFrame,
    equity_comparison: pd.DataFrame,
) -> dict[str, Any]:
    first_order = None if order_comparison.empty else order_comparison.iloc[0].to_dict()
    first_equity = None if equity_comparison.empty else equity_comparison.iloc[0].to_dict()
    categories = {}
    if not order_comparison.empty:
        categories.update(order_comparison["category"].value_counts().to_dict())
    if not equity_comparison.empty:
        categories.update({f"equity_{k}": v for k, v in equity_comparison["category"].value_counts().to_dict().items()})
    return {
        "simulator_total_return": simulator_metrics.get("total_return"),
        "backtrader_total_return": backtrader_metrics.get("total_return"),
        "total_return_diff": _metric_diff(simulator_metrics, backtrader_metrics, "total_return"),
        "simulator_sharpe": simulator_metrics.get("sharpe"),
        "backtrader_sharpe": backtrader_metrics.get("sharpe"),
        "sharpe_diff": _metric_diff(simulator_metrics, backtrader_metrics, "sharpe"),
        "simulator_max_drawdown": simulator_metrics.get("max_drawdown"),
        "backtrader_max_drawdown": backtrader_metrics.get("max_drawdown"),
        "max_drawdown_diff": _metric_diff(simulator_metrics, backtrader_metrics, "max_drawdown"),
        "simulator_filled_orders": int(simulator_orders["status"].eq("filled").sum()) if not simulator_orders.empty else 0,
        "backtrader_filled_orders": int(backtrader_orders["status"].eq("filled").sum()) if not backtrader_orders.empty else 0,
        "simulator_rejected_orders": int(simulator_orders["status"].eq("rejected").sum()) if not simulator_orders.empty else 0,
        "backtrader_rejected_orders": int(backtrader_orders["status"].eq("rejected").sum()) if not backtrader_orders.empty else 0,
        "first_order_divergence": first_order,
        "first_equity_divergence": first_equity,
        "order_divergence_count": int(len(order_comparison)),
        "equity_divergence_count": int(len(equity_comparison)),
        "divergence_categories": categories,
    }


def _metric_diff(left: dict[str, Any], right: dict[str, Any], key: str) -> float | None:
    left_value = left.get(key)
    right_value = right.get(key)
    if left_value is None or right_value is None:
        return None
    return float(left_value) - float(right_value)


def _export_gap_artifacts(out: Path, summary: dict[str, Any], artifacts: dict[str, pd.DataFrame]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summary]).to_json(out / "summary.json", orient="records", indent=2, force_ascii=False)
    for name, frame in artifacts.items():
        frame.to_csv(out / f"{name}.csv", index=True)
