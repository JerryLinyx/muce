from __future__ import annotations

import math
from typing import Any, Mapping

import pandas as pd

from quant_backtest.backtest.metrics import compute_equity_metrics, value_frame_from_vectorbt
from quant_backtest.backtest.vectorbt_models import (
    VectorbtConfig,
    VectorbtResult,
    VectorbtSignals,
    VectorbtStrategyName,
)
from quant_backtest.backtest.vectorbt_strategies import (
    build_vectorbt_signals,
    expand_parameter_grid,
)
from quant_backtest.data.adapters import load_for_vectorbt
from quant_backtest.data.cache import ParquetCache


class VectorbtEngine:
    def __init__(self, cache: ParquetCache) -> None:
        self.cache = cache

    def load_signal_panels(self, config: VectorbtConfig) -> dict[str, pd.DataFrame]:
        return load_for_vectorbt(
            self.cache,
            config.symbols,
            start=config.start,
            end=config.end,
            source=config.source,
            adjust=config.signal_adjust,
        )

    def load_execution_close(self, config: VectorbtConfig) -> pd.DataFrame:
        panels = load_for_vectorbt(
            self.cache,
            config.symbols,
            fields=["close"],
            start=config.start,
            end=config.end,
            source=config.source,
            adjust=config.execution_adjust,
        )
        return panels["close"]

    def build_signals(
        self,
        strategy: VectorbtStrategyName,
        signal_panels: Mapping[str, pd.DataFrame],
        parameters: Mapping[str, Any],
    ) -> VectorbtSignals:
        return build_vectorbt_signals(strategy, signal_panels, parameters)

    def run(self, config: VectorbtConfig) -> VectorbtResult:
        signals, close = self._prepare_single(config)
        portfolio = _portfolio_from_strategy(close, signals, config)
        metrics = _metrics_from_portfolio(
            portfolio,
            config=config,
            signals=signals,
            parameter_index=0,
        )
        return VectorbtResult(
            metrics=metrics,
            entries=signals.entries,
            exits=signals.exits,
            close=close,
            portfolio=portfolio,
            strategy=config.strategy,
        )

    def sweep(
        self,
        config: VectorbtConfig,
        parameter_grid: Mapping[str, list[Any]],
    ) -> VectorbtResult:
        parameter_sets = expand_parameter_grid(parameter_grid)
        if not parameter_sets:
            parameter_sets = [dict(config.strategy_kwargs)]

        signal_panels = self.load_signal_panels(config)
        close = self.load_execution_close(config)
        metrics_frames = []
        entries_by_param = {}
        exits_by_param = {}
        portfolios = []

        for idx, params in enumerate(parameter_sets):
            merged_params = {**dict(config.strategy_kwargs), **params}
            signals = self.build_signals(config.strategy, signal_panels, merged_params)
            portfolio = _portfolio_from_strategy(close, signals, config)
            metrics_frames.append(
                _metrics_from_portfolio(
                    portfolio,
                    config=config,
                    signals=signals,
                    parameter_index=idx,
                )
            )
            entries_by_param[idx] = signals.entries
            exits_by_param[idx] = signals.exits
            portfolios.append(portfolio)

        metrics = pd.concat(metrics_frames, ignore_index=True)
        entries = _stack_signal_frames(entries_by_param, "parameter_index")
        exits = _stack_signal_frames(exits_by_param, "parameter_index")
        return VectorbtResult(
            metrics=metrics,
            entries=entries,
            exits=exits,
            close=close,
            portfolio=portfolios,
            strategy=config.strategy,
        )

    def _prepare_single(self, config: VectorbtConfig) -> tuple[VectorbtSignals, pd.DataFrame]:
        signal_panels = self.load_signal_panels(config)
        close = self.load_execution_close(config)
        signals = self.build_signals(config.strategy, signal_panels, config.strategy_kwargs)
        return signals, close


def _portfolio_from_strategy(
    close: pd.DataFrame,
    signals: VectorbtSignals,
    config: VectorbtConfig,
) -> Any:
    if _uses_pyramiding(signals.parameters):
        target_orders = _build_pyramiding_target_orders(
            close,
            signals.entries,
            signals.exits,
            add_percent=float(signals.parameters.get("target_percent", 0.95)),
            max_position_percent=float(signals.parameters.get("max_position_percent", 1.0)),
            max_hold_days=signals.parameters.get("max_hold_days"),
            stop_loss=signals.parameters.get("stop_loss"),
            take_profit=signals.parameters.get("take_profit"),
        )
        return _portfolio_from_target_percent_orders(
            close,
            target_orders,
            cash=config.cash,
            fees=config.commission_rate,
            slippage=config.slippage_rate,
            size_granularity=config.size_granularity,
        )

    return _portfolio_from_signals(
        close,
        signals.entries,
        signals.exits,
        cash=config.cash,
        fees=config.commission_rate,
        slippage=config.slippage_rate,
        size=float(signals.parameters.get("target_percent", 0.95)),
        size_granularity=config.size_granularity,
        sl_stop=_stop_loss_to_vectorbt(signals.parameters.get("stop_loss")),
        tp_stop=_take_profit_to_vectorbt(signals.parameters.get("take_profit")),
    )


def _portfolio_from_signals(
    close: pd.DataFrame,
    entries: pd.DataFrame,
    exits: pd.DataFrame,
    *,
    cash: float,
    fees: float,
    slippage: float,
    size: float,
    size_granularity: float,
    sl_stop: float | None,
    tp_stop: float | None,
) -> Any:
    try:
        import vectorbt as vbt
    except ImportError as exc:
        raise RuntimeError(
            "vectorbt is required for research sweeps; install with quant-backtest[research]"
        ) from exc
    return vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=cash,
        size=size,
        size_type="percent",
        size_granularity=size_granularity,
        fees=fees,
        slippage=slippage,
        sl_stop=sl_stop,
        tp_stop=tp_stop,
        freq="1D",
    )


def _portfolio_from_target_percent_orders(
    close: pd.DataFrame,
    target_orders: pd.DataFrame,
    *,
    cash: float,
    fees: float,
    slippage: float,
    size_granularity: float,
) -> Any:
    try:
        import vectorbt as vbt
    except ImportError as exc:
        raise RuntimeError(
            "vectorbt is required for research sweeps; install with quant-backtest[research]"
        ) from exc
    return vbt.Portfolio.from_orders(
        close,
        size=target_orders,
        size_type="targetpercent",
        init_cash=cash,
        size_granularity=size_granularity,
        fees=fees,
        slippage=slippage,
        freq="1D",
    )


def _build_pyramiding_target_orders(
    close: pd.DataFrame,
    entries: pd.DataFrame,
    exits: pd.DataFrame,
    *,
    add_percent: float,
    max_position_percent: float,
    max_hold_days: Any,
    stop_loss: Any,
    take_profit: Any,
) -> pd.DataFrame:
    if add_percent <= 0:
        raise ValueError("target_percent must be positive when pyramiding is enabled")
    if max_position_percent <= 0:
        raise ValueError("max_position_percent must be positive when pyramiding is enabled")

    max_hold = None if max_hold_days is None else int(max_hold_days)
    stop = None if stop_loss is None else float(stop_loss)
    profit = None if take_profit is None else float(take_profit)
    target_orders = pd.DataFrame(math.nan, index=close.index, columns=close.columns, dtype=float)
    entry_events = entries.reindex(index=close.index, columns=close.columns, fill_value=False).astype(bool)
    exit_events = exits.reindex(index=close.index, columns=close.columns, fill_value=False).astype(bool)

    for symbol in close.columns:
        target = 0.0
        entry_bar: int | None = None
        average_entry_price: float | None = None
        prices = close[symbol]
        symbol_entries = entry_events[symbol]
        symbol_exits = exit_events[symbol]

        for idx, price in enumerate(prices):
            if pd.isna(price):
                continue
            price = float(price)
            should_exit = False
            if target > 0 and average_entry_price:
                change = price / average_entry_price - 1.0
                should_exit = bool(symbol_exits.iloc[idx])
                if max_hold is not None and entry_bar is not None:
                    should_exit = should_exit or idx - entry_bar >= max_hold
                if stop is not None:
                    should_exit = should_exit or change <= stop
                if profit is not None:
                    should_exit = should_exit or change >= profit

            if should_exit:
                target_orders.iat[idx, target_orders.columns.get_loc(symbol)] = 0.0
                target = 0.0
                entry_bar = None
                average_entry_price = None
                continue

            if bool(symbol_entries.iloc[idx]):
                next_target = min(max_position_percent, target + add_percent)
                if next_target <= target:
                    continue
                if target == 0:
                    average_entry_price = price
                    entry_bar = idx
                elif average_entry_price is not None:
                    added_weight = next_target - target
                    average_entry_price = (
                        average_entry_price * target + price * added_weight
                    ) / next_target
                target = next_target
                target_orders.iat[idx, target_orders.columns.get_loc(symbol)] = target

    return target_orders


def _metrics_from_portfolio(
    portfolio: Any,
    *,
    config: VectorbtConfig,
    signals: VectorbtSignals,
    parameter_index: int,
) -> pd.DataFrame:
    values = value_frame_from_vectorbt(portfolio)
    trades = portfolio.trades
    trade_count = _series_metric(trades.count(), cast=int)
    win_rate = _series_metric(trades.win_rate())

    rows = []
    for symbol in values.columns:
        common_metrics = compute_equity_metrics(values[symbol], start_cash=config.cash)
        row = {
            "parameter_index": parameter_index,
            "symbol": str(symbol),
            "strategy": config.strategy,
            **common_metrics,
            "annual_return_pct": (
                common_metrics["annual_return"] * 100
                if common_metrics["annual_return"] is not None
                else None
            ),
            "max_drawdown_pct": (
                common_metrics["max_drawdown"] * 100
                if common_metrics["max_drawdown"] is not None
                else None
            ),
            "trade_count": int(trade_count.loc[symbol]),
            "win_rate": _optional_float(win_rate.loc[symbol]),
            "entry_count": int(signals.entries[str(symbol)].sum()),
            "exit_count": int(signals.exits[str(symbol)].sum()),
        }
        row.update({f"param_{key}": value for key, value in signals.parameters.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def _series_metric(value: Any, *, cast: type | None = None) -> pd.Series:
    if isinstance(value, pd.Series):
        series = value
    else:
        series = pd.Series(value)
    if cast is not None:
        return series.fillna(0).astype(cast)
    return series


def _optional_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _stack_signal_frames(frames: Mapping[int, pd.DataFrame], name: str) -> pd.DataFrame:
    pieces = []
    for idx, frame in frames.items():
        current = frame.copy()
        current.columns = pd.MultiIndex.from_product([[idx], current.columns], names=[name, "symbol"])
        pieces.append(current)
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, axis=1)


def _uses_pyramiding(parameters: Mapping[str, Any]) -> bool:
    return bool(parameters.get("pyramiding") or parameters.get("allow_pyramiding"))


def _stop_loss_to_vectorbt(value: Any) -> float | None:
    if value is None:
        return None
    value = float(value)
    if value == 0:
        return None
    return abs(value)


def _take_profit_to_vectorbt(value: Any) -> float | None:
    if value is None:
        return None
    value = float(value)
    if value == 0:
        return None
    return abs(value)
