from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from quant_backtest.backtest.analyzers import get_analyzer_classes
from quant_backtest.backtest.feeds import make_ashare_feed
from quant_backtest.backtest.metrics import compute_equity_metrics
from quant_backtest.backtest.models import BacktraderConfig, BacktraderResult
from quant_backtest.data.adapters import load_backtrader_signal_execution_frame
from quant_backtest.data.cache import ParquetCache


class BacktraderEngine:
    def __init__(self, cache: ParquetCache) -> None:
        self.cache = cache

    def load_data_frame(self, symbol: str, config: BacktraderConfig) -> pd.DataFrame:
        return load_backtrader_signal_execution_frame(
            self.cache,
            symbol,
            start=config.start,
            end=config.end,
            source=config.source,
            signal_adjust=config.signal_adjust,
            execution_adjust=config.execution_adjust,
        )

    def run(
        self,
        strategy_factory: Callable[..., Any],
        config: BacktraderConfig,
    ) -> BacktraderResult:
        try:
            import backtrader as bt
        except ImportError as exc:
            raise RuntimeError(
                "backtrader is required for validation; install with quant-backtest[validation]"
            ) from exc

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(config.cash)
        cerebro.broker.setcommission(commission=config.commission_rate)
        cerebro.broker.set_slippage_perc(perc=config.slippage_rate)
        if config.execution_timing == "same_close":
            cerebro.broker.set_coc(True)

        for symbol in config.symbols:
            frame = self.load_data_frame(symbol, config)
            if frame.empty:
                raise ValueError(f"no cached rows available for {symbol}")
            cerebro.adddata(make_ashare_feed(frame, name=symbol), name=symbol)

        cerebro.addstrategy(strategy_factory, **dict(config.strategy_kwargs))

        equity_analyzer, order_analyzer, trade_analyzer = get_analyzer_classes()
        cerebro.addanalyzer(equity_analyzer, _name="equity_curve")
        cerebro.addanalyzer(order_analyzer, _name="orders")
        cerebro.addanalyzer(trade_analyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days)
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

        strategies = cerebro.run()
        strategy = strategies[0]
        final_value = float(cerebro.broker.getvalue())
        raw_analyzers = {
            name: analyzer.get_analysis()
            for name, analyzer in strategy.analyzers.getitems()
        }
        equity = _frame(raw_analyzers["equity_curve"])
        orders = _frame(raw_analyzers["orders"])
        trades = _frame(raw_analyzers["trades"])
        metrics = _build_metrics(
            start_cash=config.cash,
            equity=equity,
            orders=orders,
            trades=trades,
        )
        return BacktraderResult(
            metrics=metrics,
            equity_curve=equity,
            orders=orders,
            trades=trades,
            raw_analyzers=raw_analyzers,
            final_value=final_value,
            start_cash=config.cash,
        )


def _frame(rows: Any) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _build_metrics(
    *,
    start_cash: float,
    equity: pd.DataFrame,
    orders: pd.DataFrame,
    trades: pd.DataFrame,
) -> dict[str, float | int | None]:
    if equity.empty:
        metrics = compute_equity_metrics(pd.Series(dtype=float), start_cash=start_cash)
    else:
        metrics = compute_equity_metrics(equity["value"], start_cash=start_cash)
    completed_orders = 0
    if not orders.empty and "status" in orders:
        completed_orders = int(orders["status"].eq("Completed").sum())
    metrics["annual_return_pct"] = (
        metrics["annual_return"] * 100 if metrics["annual_return"] is not None else None
    )
    metrics["max_drawdown_pct"] = (
        metrics["max_drawdown"] * 100 if metrics["max_drawdown"] is not None else None
    )
    metrics["order_count"] = completed_orders
    metrics["trade_count"] = int(len(trades))
    return metrics
