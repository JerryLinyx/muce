from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from typing import Any, Literal

import pandas as pd

from quant_backtest.backtest.metrics import compute_equity_metrics
from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import Adjust, SOURCE_BAOSTOCK
from quant_backtest.selection.factors import FactorSelectorConfig, build_factor_table, select_candidates

PriceField = Literal["open", "close"]


@dataclass(frozen=True)
class SelectionExecutionConfig:
    symbols: list[str]
    start: str | None = None
    end: str | None = None
    source: str = SOURCE_BAOSTOCK
    signal_adjust: Adjust = "qfq"
    execution_adjust: Adjust = "raw"
    cash: float = 1_000_000.0
    commission_bps: float = 3.0
    slippage_bps: float = 5.0
    surge_threshold_pct: float | None = 0.03
    surge_extra_slippage_bps: float = 20.0
    hold_days: int = 1
    entry_lag_days: int = 0
    entry_price_field: PriceField = "close"
    exit_price_field: PriceField = "close"
    target_percent_per_position: float = 0.1
    max_positions: int = 1
    lot_size: int = 100
    reject_limit_up_buy: bool = True
    reject_limit_down_sell: bool = True
    take_profit_pct: float | None = None
    stop_loss_pct: float | None = None
    top_n: int = 1
    selector: FactorSelectorConfig = FactorSelectorConfig(top_n=1)

    @property
    def commission_rate(self) -> float:
        return self.commission_bps / 10_000

    @property
    def slippage_rate(self) -> float:
        return self.slippage_bps / 10_000

    @property
    def surge_extra_slippage_rate(self) -> float:
        return self.surge_extra_slippage_bps / 10_000


@dataclass
class Position:
    symbol: str
    shares: int
    entry_date: pd.Timestamp
    entry_index: int
    entry_price: float
    last_price: float


@dataclass(frozen=True)
class ExecutionSimulationContext:
    execution_data: pd.DataFrame
    factor_table: pd.DataFrame
    bars: dict[tuple[pd.Timestamp, str], Any]
    trading_dates: list[pd.Timestamp]


def run_selection_execution_simulation(cache: ParquetCache, config: SelectionExecutionConfig) -> dict[str, Any]:
    _validate_config(config)
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
    execution_data = execution_data.sort_values(["date", "symbol"]).copy()
    execution_data["date"] = pd.to_datetime(execution_data["date"])
    factor_table = build_factor_table(signal_data, config.selector)
    candidates = select_candidates(factor_table, top_n=config.top_n)
    return run_selection_execution_simulation_from_data(
        execution_data=execution_data,
        factor_table=factor_table,
        candidates=candidates,
        config=config,
    )


def run_selection_execution_simulation_from_data(
    *,
    execution_data: pd.DataFrame,
    factor_table: pd.DataFrame,
    candidates: pd.DataFrame,
    config: SelectionExecutionConfig,
) -> dict[str, Any]:
    _validate_config(config)
    context = prepare_execution_simulation_context(
        execution_data=execution_data,
        factor_table=factor_table,
    )
    return run_selection_execution_simulation_from_context(
        context=context,
        candidates=candidates,
        config=config,
    )


def prepare_execution_simulation_context(
    *,
    execution_data: pd.DataFrame,
    factor_table: pd.DataFrame,
) -> ExecutionSimulationContext:
    execution_data = execution_data.sort_values(["date", "symbol"]).copy()
    execution_data["date"] = pd.to_datetime(execution_data["date"])
    return ExecutionSimulationContext(
        execution_data=execution_data,
        factor_table=factor_table,
        bars={(row.date, row.symbol): row for row in execution_data.itertuples(index=False)},
        trading_dates=list(execution_data["date"].drop_duplicates().sort_values()),
    )


def run_selection_execution_simulation_from_context(
    *,
    context: ExecutionSimulationContext,
    candidates: pd.DataFrame,
    config: SelectionExecutionConfig,
) -> dict[str, Any]:
    _validate_config(config)
    entries_by_date = _schedule_entries(candidates, context.trading_dates, config.entry_lag_days)

    cash = float(config.cash)
    positions: dict[str, Position] = {}
    orders: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []

    for idx, date in enumerate(context.trading_dates):
        cash_ref = {"cash": cash}
        _process_exits(
            date=date,
            date_index=idx,
            positions=positions,
            bars=context.bars,
            orders=orders,
            config=config,
            cash_ref=cash_ref,
        )
        cash = cash_ref["cash"]

        current_value = _portfolio_value(cash, positions, context.bars, date)
        todays_candidates = entries_by_date.get(date, pd.DataFrame())
        for row in todays_candidates.itertuples(index=False):
            if len(positions) >= config.max_positions:
                _record_rejection(orders, date, row.symbol, "buy", "max_positions", cash)
                continue
            if row.symbol in positions:
                _record_rejection(orders, date, row.symbol, "buy", "already_holding", cash)
                continue
            bar = context.bars.get((date, row.symbol))
            if bar is None or int(getattr(bar, "trade_status", 1)) != 1:
                _record_rejection(orders, date, row.symbol, "buy", "not_tradable", cash)
                continue
            raw_entry_price = _bar_price(bar, config.entry_price_field)
            if raw_entry_price is None or raw_entry_price <= 0:
                _record_rejection(orders, date, row.symbol, "buy", "missing_entry_price", cash)
                continue
            if config.reject_limit_up_buy and _is_limit_up(bar, raw_entry_price):
                _record_rejection(orders, date, row.symbol, "buy", "limit_up_buy_blocked", cash)
                continue

            slippage = config.slippage_rate + _surge_slippage(bar, raw_entry_price, config)
            fill_price = raw_entry_price * (1 + slippage)
            target_value = current_value * config.target_percent_per_position
            shares = _round_lot(target_value / fill_price, config.lot_size)
            max_affordable = _round_lot(cash / (fill_price * (1 + config.commission_rate)), config.lot_size)
            shares = min(shares, max_affordable)
            if shares <= 0:
                _record_rejection(orders, date, row.symbol, "buy", "insufficient_cash_or_lot", cash)
                continue

            gross = fill_price * shares
            commission = gross * config.commission_rate
            cash -= gross + commission
            positions[row.symbol] = Position(
                symbol=row.symbol,
                shares=shares,
                entry_date=date,
                entry_index=idx,
                entry_price=fill_price,
                last_price=raw_entry_price,
            )
            orders.append(
                {
                    "date": date,
                    "symbol": row.symbol,
                    "side": "buy",
                    "status": "filled",
                    "reason": "entry",
                    "shares": shares,
                    "raw_price": raw_entry_price,
                    "fill_price": fill_price,
                    "commission": commission,
                    "cash_after": cash,
                    "cash_after_date": date,
                }
            )

        equity_rows.append(
            {
                "date": date,
                "cash": cash,
                "market_value": _market_value(positions, context.bars, date),
                "value": _portfolio_value(cash, positions, context.bars, date),
                "position_count": len(positions),
            }
        )

    equity = pd.DataFrame(equity_rows).set_index("date")
    order_frame = pd.DataFrame(orders)
    metrics = compute_equity_metrics(equity["value"], start_cash=config.cash)
    metrics.update(_order_metrics(order_frame))
    metrics["annual_return_pct"] = metrics["annual_return"] * 100 if metrics["annual_return"] is not None else None
    metrics["max_drawdown_pct"] = metrics["max_drawdown"] * 100 if metrics["max_drawdown"] is not None else None
    metrics["candidate_count"] = int(len(candidates))
    metrics["hold_days"] = int(config.hold_days)
    metrics["entry_lag_days"] = int(config.entry_lag_days)
    metrics["target_percent_per_position"] = float(config.target_percent_per_position)
    metrics["max_positions"] = int(config.max_positions)
    return {
        "metrics": metrics,
        "factor_table": context.factor_table,
        "candidates": candidates,
        "orders": order_frame,
        "equity": equity,
    }


def sweep_selection_execution(
    cache: ParquetCache,
    base_config: SelectionExecutionConfig,
    *,
    hold_days: list[int],
    target_percents: list[float],
    max_positions: list[int],
    top_ns: list[int],
    stop_losses: list[float | None],
    take_profits: list[float | None],
    entry_lag_days: list[int],
    min_scores: list[int] | None = None,
    rsi_thresholds: list[float] | None = None,
    volume_multipliers: list[float] | None = None,
    boll_stds: list[float] | None = None,
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
    execution_data = execution_data.sort_values(["date", "symbol"]).copy()
    execution_data["date"] = pd.to_datetime(execution_data["date"])
    min_scores = min_scores or [base_config.selector.min_score]
    rsi_thresholds = rsi_thresholds or [base_config.selector.rsi_threshold]
    volume_multipliers = volume_multipliers or [base_config.selector.volume_multiplier]
    boll_stds = boll_stds or [base_config.selector.boll_std]

    rows: list[dict[str, Any]] = []
    for min_score, rsi_threshold, volume_multiplier, boll_std in product(
        min_scores,
        rsi_thresholds,
        volume_multipliers,
        boll_stds,
    ):
        selector = replace(
            base_config.selector,
            min_score=min_score,
            rsi_threshold=rsi_threshold,
            volume_multiplier=volume_multiplier,
            boll_std=boll_std,
        )
        factor_table = build_factor_table(signal_data, selector)
        context = prepare_execution_simulation_context(
            execution_data=execution_data,
            factor_table=factor_table,
        )
        for (
            hold_day,
            target_percent,
            max_position,
            top_n,
            stop_loss,
            take_profit,
            entry_lag_day,
        ) in product(hold_days, target_percents, max_positions, top_ns, stop_losses, take_profits, entry_lag_days):
            config = replace(
                base_config,
                hold_days=hold_day,
                target_percent_per_position=target_percent,
                max_positions=max_position,
                top_n=top_n,
                stop_loss_pct=stop_loss,
                take_profit_pct=take_profit,
                entry_lag_days=entry_lag_day,
                selector=selector,
            )
            candidates = _select_candidates_preserving_filters(factor_table, top_n=top_n)
            result = run_selection_execution_simulation_from_context(
                context=context,
                candidates=candidates,
                config=config,
            )
            rows.append(
                {
                    "min_score": min_score,
                    "rsi_threshold": rsi_threshold,
                    "volume_multiplier": volume_multiplier,
                    "boll_std": boll_std,
                    "hold_days": hold_day,
                    "target_percent_per_position": target_percent,
                    "max_positions": max_position,
                    "top_n": top_n,
                    "stop_loss_pct": stop_loss,
                    "take_profit_pct": take_profit,
                    "entry_lag_days": entry_lag_day,
                    **result["metrics"],
                }
            )
    return pd.DataFrame(rows)


def _select_candidates_preserving_filters(factor_table: pd.DataFrame, *, top_n: int) -> pd.DataFrame:
    return select_candidates(factor_table, top_n=top_n)


def _validate_config(config: SelectionExecutionConfig) -> None:
    if config.hold_days < 1:
        raise ValueError("hold_days must be >= 1")
    if config.entry_lag_days < 0:
        raise ValueError("entry_lag_days must be >= 0")
    if config.target_percent_per_position <= 0:
        raise ValueError("target_percent_per_position must be positive")
    if config.max_positions < 1:
        raise ValueError("max_positions must be >= 1")
    if config.lot_size < 1:
        raise ValueError("lot_size must be >= 1")


def _schedule_entries(candidates: pd.DataFrame, trading_dates: list[pd.Timestamp], entry_lag_days: int) -> dict[pd.Timestamp, pd.DataFrame]:
    if candidates.empty:
        return {}
    date_to_index = {date: idx for idx, date in enumerate(trading_dates)}
    frames: dict[pd.Timestamp, list[dict[str, Any]]] = {}
    for row in candidates.itertuples(index=False):
        signal_date = pd.Timestamp(row.date)
        if signal_date not in date_to_index:
            continue
        entry_index = date_to_index[signal_date] + entry_lag_days
        if entry_index >= len(trading_dates):
            continue
        entry_date = trading_dates[entry_index]
        frames.setdefault(entry_date, []).append(row._asdict())
    return {date: pd.DataFrame(rows) for date, rows in frames.items()}


def _process_exits(
    *,
    date: pd.Timestamp,
    date_index: int,
    positions: dict[str, Position],
    bars: dict[tuple[pd.Timestamp, str], Any],
    orders: list[dict[str, Any]],
    config: SelectionExecutionConfig,
    cash_ref: dict[str, float],
) -> None:
    cash = cash_ref["cash"]
    for symbol, position in list(positions.items()):
        bar = bars.get((date, symbol))
        if bar is None:
            continue
        raw_exit_price, reason = _exit_price_and_reason(position, bar, date_index, config)
        if raw_exit_price is None:
            position.last_price = _bar_price(bar, "close") or position.last_price
            continue
        if config.reject_limit_down_sell and _is_limit_down(bar, raw_exit_price):
            _record_rejection(orders, date, symbol, "sell", "limit_down_sell_blocked", cash)
            position.last_price = _bar_price(bar, "close") or position.last_price
            continue
        fill_price = raw_exit_price * (1 - config.slippage_rate)
        gross = fill_price * position.shares
        commission = gross * config.commission_rate
        cash += gross - commission
        orders.append(
            {
                "date": date,
                "symbol": symbol,
                "side": "sell",
                "status": "filled",
                "reason": reason,
                "shares": position.shares,
                "raw_price": raw_exit_price,
                "fill_price": fill_price,
                "commission": commission,
                "cash_after": cash,
                "cash_after_date": date,
                "pnl": (fill_price - position.entry_price) * position.shares - commission,
                "return": fill_price / position.entry_price - 1,
            }
        )
        del positions[symbol]
    cash_ref["cash"] = cash


def _exit_price_and_reason(
    position: Position,
    bar: Any,
    date_index: int,
    config: SelectionExecutionConfig,
) -> tuple[float | None, str | None]:
    days_held = date_index - position.entry_index
    if days_held <= 0:
        return None, None
    stop_price = None
    take_price = None
    if config.stop_loss_pct is not None:
        stop_price = position.entry_price * (1 + config.stop_loss_pct)
    if config.take_profit_pct is not None:
        take_price = position.entry_price * (1 + config.take_profit_pct)
    low = float(getattr(bar, "low"))
    high = float(getattr(bar, "high"))
    if stop_price is not None and low <= stop_price:
        return stop_price, "stop_loss"
    if take_price is not None and high >= take_price:
        return take_price, "take_profit"
    if days_held >= config.hold_days:
        price = _bar_price(bar, config.exit_price_field)
        return price, "time_exit"
    return None, None


def _bar_price(bar: Any, field: PriceField) -> float | None:
    value = getattr(bar, field)
    if pd.isna(value):
        return None
    return float(value)


def _limit_pct(bar: Any) -> float:
    symbol = str(getattr(bar, "symbol"))
    is_st = int(getattr(bar, "is_st", 0)) == 1
    if is_st:
        return 0.05
    if symbol.startswith(("300", "301", "688", "689")):
        return 0.20
    return 0.10


def _is_limit_up(bar: Any, price: float) -> bool:
    pre_close = float(getattr(bar, "pre_close", 0) or 0)
    if pre_close <= 0:
        return False
    return price >= pre_close * (1 + _limit_pct(bar)) * 0.999


def _is_limit_down(bar: Any, price: float) -> bool:
    pre_close = float(getattr(bar, "pre_close", 0) or 0)
    if pre_close <= 0:
        return False
    return price <= pre_close * (1 - _limit_pct(bar)) * 1.001


def _surge_slippage(bar: Any, entry_price: float, config: SelectionExecutionConfig) -> float:
    if config.surge_threshold_pct is None:
        return 0.0
    pre_close = float(getattr(bar, "pre_close", 0) or 0)
    if pre_close <= 0:
        return 0.0
    if entry_price / pre_close - 1 >= config.surge_threshold_pct:
        return config.surge_extra_slippage_rate
    return 0.0


def _round_lot(shares: float, lot_size: int) -> int:
    return int(shares // lot_size * lot_size)


def _market_value(positions: dict[str, Position], bars: dict[tuple[pd.Timestamp, str], Any], date: pd.Timestamp) -> float:
    total = 0.0
    for symbol, position in positions.items():
        bar = bars.get((date, symbol))
        if bar is not None:
            close = _bar_price(bar, "close")
            if close is not None:
                position.last_price = close
        total += position.shares * position.last_price
    return total


def _portfolio_value(cash: float, positions: dict[str, Position], bars: dict[tuple[pd.Timestamp, str], Any], date: pd.Timestamp) -> float:
    return cash + _market_value(positions, bars, date)


def _record_rejection(
    orders: list[dict[str, Any]],
    date: pd.Timestamp,
    symbol: str,
    side: str,
    reason: str,
    cash: float,
) -> None:
    orders.append(
        {
            "date": date,
            "symbol": symbol,
            "side": side,
            "status": "rejected",
            "reason": reason,
            "shares": 0,
            "raw_price": None,
            "fill_price": None,
            "commission": 0.0,
            "cash_after": cash,
            "cash_after_date": date,
        }
    )


def _order_metrics(order_frame: pd.DataFrame) -> dict[str, Any]:
    if order_frame.empty:
        return {
            "filled_buy_count": 0,
            "filled_sell_count": 0,
            "rejected_buy_count": 0,
            "rejected_sell_count": 0,
            "limit_up_buy_rejections": 0,
            "limit_down_sell_rejections": 0,
            "cash_or_lot_rejections": 0,
            "trade_win_rate": None,
        }
    filled = order_frame["status"].eq("filled")
    rejected = order_frame["status"].eq("rejected")
    sells = order_frame["side"].eq("sell")
    filled_sells = order_frame[filled & sells]
    trade_win_rate = None
    if not filled_sells.empty and "return" in filled_sells.columns:
        trade_win_rate = float(filled_sells["return"].gt(0).sum() / len(filled_sells))
    return {
        "filled_buy_count": int((filled & order_frame["side"].eq("buy")).sum()),
        "filled_sell_count": int((filled & sells).sum()),
        "rejected_buy_count": int((rejected & order_frame["side"].eq("buy")).sum()),
        "rejected_sell_count": int((rejected & sells).sum()),
        "limit_up_buy_rejections": int(order_frame["reason"].eq("limit_up_buy_blocked").sum()),
        "limit_down_sell_rejections": int(order_frame["reason"].eq("limit_down_sell_blocked").sum()),
        "cash_or_lot_rejections": int(order_frame["reason"].eq("insufficient_cash_or_lot").sum()),
        "trade_win_rate": trade_win_rate,
    }
