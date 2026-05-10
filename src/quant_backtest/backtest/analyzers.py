from __future__ import annotations

from typing import Any


def get_analyzer_classes() -> tuple[Any, Any, Any]:
    try:
        import backtrader as bt
    except ImportError as exc:
        raise RuntimeError(
            "backtrader is required for analyzers; install with quant-backtest[validation]"
        ) from exc

    class EquityCurveAnalyzer(bt.Analyzer):
        def start(self) -> None:
            self.rows: list[dict[str, Any]] = []

        def next(self) -> None:
            self.rows.append(
                {
                    "date": self.strategy.datetime.date(0).isoformat(),
                    "value": float(self.strategy.broker.getvalue()),
                    "cash": float(self.strategy.broker.getcash()),
                }
            )

        def get_analysis(self) -> list[dict[str, Any]]:
            return self.rows

    class OrderLogAnalyzer(bt.Analyzer):
        def start(self) -> None:
            self.rows: list[dict[str, Any]] = []

        def notify_order(self, order: Any) -> None:
            if order.status not in [
                order.Submitted,
                order.Accepted,
                order.Completed,
                order.Canceled,
                order.Margin,
                order.Rejected,
            ]:
                return
            executed = order.executed
            log_date = self.strategy.datetime.date(0).isoformat()
            if order.status == order.Completed and executed.dt:
                log_date = bt.num2date(executed.dt).date().isoformat()
            self.rows.append(
                {
                    "date": log_date,
                    "symbol": order.data._name,
                    "ref": int(order.ref),
                    "status": order.getstatusname(),
                    "side": "buy" if order.isbuy() else "sell",
                    "created_size": float(order.created.size),
                    "created_price": float(order.created.price or 0.0),
                    "executed_size": float(executed.size),
                    "executed_price": float(executed.price),
                    "executed_value": float(executed.value),
                    "commission": float(executed.comm),
                }
            )

        def get_analysis(self) -> list[dict[str, Any]]:
            return self.rows

    class TradeLogAnalyzer(bt.Analyzer):
        def start(self) -> None:
            self.rows: list[dict[str, Any]] = []

        def notify_trade(self, trade: Any) -> None:
            if not trade.isclosed:
                return
            self.rows.append(
                {
                    "date": self.strategy.datetime.date(0).isoformat(),
                    "symbol": trade.data._name,
                    "ref": int(trade.ref),
                    "size": float(trade.size),
                    "price": float(trade.price),
                    "pnl": float(trade.pnl),
                    "pnl_comm": float(trade.pnlcomm),
                    "commission": float(trade.commission),
                    "bar_len": int(trade.barlen),
                }
            )

        def get_analysis(self) -> list[dict[str, Any]]:
            return self.rows

    return EquityCurveAnalyzer, OrderLogAnalyzer, TradeLogAnalyzer
