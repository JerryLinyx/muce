from __future__ import annotations

from typing import Any


def _has_pending_order(strategy: Any) -> bool:
    broker_orders = getattr(strategy.broker, "orders", [])
    return any(order.alive() for order in broker_orders)


def _is_n_rising(data: Any, count: int) -> bool:
    return all(data.signal_close[-offset] > data.signal_open[-offset] for offset in range(count))


def _is_n_falling(data: Any, count: int) -> bool:
    return all(data.signal_close[-offset] < data.signal_open[-offset] for offset in range(count))


def _limit_pct_for_data(data: Any) -> float:
    symbol = str(data._name)
    is_st = bool(int(data.is_st[0])) if hasattr(data, "is_st") else False
    if is_st:
        return 0.05
    if symbol.startswith(("300", "301", "688", "689")):
        return 0.20
    return 0.10


def _is_limit_up(data: Any) -> bool:
    return _is_limit_up_at(data, float(data.close[0]))


def _is_limit_up_at(data: Any, price: float) -> bool:
    pre_close = float(data.pre_close[0]) if hasattr(data, "pre_close") else 0.0
    if pre_close <= 0:
        return False
    return price >= pre_close * (1 + _limit_pct_for_data(data)) * 0.999


def _is_limit_down(data: Any) -> bool:
    pre_close = float(data.pre_close[0]) if hasattr(data, "pre_close") else 0.0
    if pre_close <= 0:
        return False
    return float(data.close[0]) <= pre_close * (1 - _limit_pct_for_data(data)) * 1.001


def get_precomputed_selector_strategy_class() -> Any:
    try:
        import backtrader as bt
    except ImportError as exc:
        raise RuntimeError(
            "backtrader is required for strategies; install with quant-backtest[validation]"
        ) from exc

    class PrecomputedSelectorStrategy(bt.Strategy):
        params = (
            ("signals_by_symbol", {}),
            ("signals_by_date", {}),
            ("execution_timing", "same_close"),
            ("target_percent", 0.2),
            ("hold_bars", 5),
            ("max_positions", 1),
            ("lot_size", 100),
            ("slippage_bps", 5.0),
            ("take_profit_pct", None),
            ("stop_loss_pct", None),
            ("reject_limit_up_buy", True),
            ("reject_limit_down_sell", True),
        )

        def __init__(self) -> None:
            self.entry_bar_by_data: dict[Any, int] = {}
            self.entry_price_by_data: dict[Any, float] = {}
            self.data_by_symbol = {data._name: data for data in self.datas}

        def next(self) -> None:
            if _has_pending_order(self):
                return

            self._process_exits()
            self._process_entries(price_field="close")

        def _process_exits(self) -> None:
            for data in self.datas:
                position = self.getposition(data)
                if not position:
                    continue
                entry_bar = self.entry_bar_by_data.get(data)
                entry_price = self.entry_price_by_data.get(data)
                if entry_bar is None or entry_price is None:
                    continue

                reached_take_profit = (
                    self.p.take_profit_pct is not None
                    and float(data.close[0]) >= entry_price * (1 + self.p.take_profit_pct)
                )
                reached_stop_loss = (
                    self.p.stop_loss_pct is not None
                    and float(data.close[0]) <= entry_price * (1 + self.p.stop_loss_pct)
                )
                reached_time_exit = len(data) - entry_bar >= self.p.hold_bars
                if not (reached_take_profit or reached_stop_loss or reached_time_exit):
                    continue
                if self.p.execution_timing == "same_close" and self.p.reject_limit_down_sell and _is_limit_down(data):
                    continue
                self.close(data=data, exectype=bt.Order.Close)

        def _process_entries(self, *, price_field: str) -> None:
            active_positions = sum(1 for data in self.datas if self.getposition(data).size)
            if active_positions >= self.p.max_positions:
                return

            date = self.datas[0].datetime.date(0).isoformat()
            signal_datas = self._signal_datas_for_date(date)
            eligible_datas = []
            for data in signal_datas:
                if self.getposition(data).size:
                    continue
                if int(data.trade_status[0]) != 1:
                    continue
                entry_price = float(getattr(data, price_field)[0])
                if self.p.execution_timing == "same_close" and self.p.reject_limit_up_buy and _is_limit_up_at(data, entry_price):
                    continue
                eligible_datas.append(data)

            open_slots = self.p.max_positions - active_positions
            for data in eligible_datas[:open_slots]:
                size = self._target_lot_size(data, price_field=price_field)
                if size <= 0:
                    continue
                self.buy(data=data, size=size)

        def _signal_datas_for_date(self, date: str) -> list[Any]:
            symbols = self.p.signals_by_date.get(date)
            if symbols is not None:
                return [self.data_by_symbol[symbol] for symbol in symbols if symbol in self.data_by_symbol]
            return [
                data
                for data in self.datas
                if date in self.p.signals_by_symbol.get(data._name, set())
            ]

        def _target_lot_size(self, data: Any, *, price_field: str) -> int:
            reference_price = float(getattr(data, price_field)[0])
            if reference_price <= 0:
                return 0
            reference_price = reference_price * (1 + float(self.p.slippage_bps) / 10_000)
            target_value = float(self.broker.getvalue()) * float(self.p.target_percent)
            raw_size = target_value / reference_price
            lot_size = int(self.p.lot_size)
            if lot_size <= 1:
                return int(raw_size)
            return int(raw_size // lot_size * lot_size)

        def notify_order(self, order: Any) -> None:
            if order.status == order.Completed and order.isbuy():
                self.entry_price_by_data[order.data] = float(order.executed.price)
                self.entry_bar_by_data[order.data] = len(order.data) - 1
                return
            if order.status == order.Completed and order.issell():
                self.entry_bar_by_data.pop(order.data, None)
                self.entry_price_by_data.pop(order.data, None)
                return
            if order.status in [order.Canceled, order.Margin, order.Rejected] and order.isbuy():
                self.entry_bar_by_data.pop(order.data, None)
                self.entry_price_by_data.pop(order.data, None)

    return PrecomputedSelectorStrategy


def get_three_falling_buy_three_rising_sell_strategy_class() -> Any:
    try:
        import backtrader as bt
    except ImportError as exc:
        raise RuntimeError(
            "backtrader is required for strategies; install with quant-backtest[validation]"
        ) from exc

    class ThreeFallingBuyThreeRisingSellStrategy(bt.Strategy):
        params = (
            ("target_percent", 0.95),
            ("signal_count", 3),
        )

        def next(self) -> None:
            if _has_pending_order(self):
                return

            for data in self.datas:
                if len(data) < self.p.signal_count:
                    continue

                position = self.getposition(data)
                if not position and _is_n_falling(data, self.p.signal_count):
                    self.order_target_percent(data=data, target=self.p.target_percent)
                elif position and _is_n_rising(data, self.p.signal_count):
                    self.order_target_percent(data=data, target=0.0)

    return ThreeFallingBuyThreeRisingSellStrategy


def get_three_rising_hold_one_day_strategy_class() -> Any:
    try:
        import backtrader as bt
    except ImportError as exc:
        raise RuntimeError(
            "backtrader is required for strategies; install with quant-backtest[validation]"
        ) from exc

    class ThreeRisingHoldOneDayStrategy(bt.Strategy):
        params = (
            ("target_percent", 0.95),
            ("hold_bars", 1),
        )

        def __init__(self) -> None:
            self.entry_bar_by_data: dict[Any, int] = {}

        def next(self) -> None:
            if _has_pending_order(self):
                return

            for data in self.datas:
                position = self.getposition(data)
                if position:
                    entry_bar = self.entry_bar_by_data.get(data)
                    if entry_bar is not None and len(data) - entry_bar >= self.p.hold_bars:
                        self.order_target_percent(data=data, target=0.0)
                    continue

                if len(data) < 3:
                    continue
                if _is_n_rising(data, 3):
                    self.order_target_percent(data=data, target=self.p.target_percent)
                    self.entry_bar_by_data[data] = len(data)

        def notify_order(self, order: Any) -> None:
            if order.status in [order.Canceled, order.Margin, order.Rejected] and order.isbuy():
                self.entry_bar_by_data.pop(order.data, None)

    return ThreeRisingHoldOneDayStrategy


def get_signal_sma_cross_strategy_class() -> Any:
    try:
        import backtrader as bt
    except ImportError as exc:
        raise RuntimeError(
            "backtrader is required for strategies; install with quant-backtest[validation]"
        ) from exc

    class SignalSmaCrossStrategy(bt.Strategy):
        params = (
            ("fast_period", 5),
            ("slow_period", 20),
            ("target_percent", 0.95),
        )

        def __init__(self) -> None:
            self.fast = {
                data: bt.indicators.SimpleMovingAverage(
                    data.signal_close,
                    period=self.p.fast_period,
                )
                for data in self.datas
            }
            self.slow = {
                data: bt.indicators.SimpleMovingAverage(
                    data.signal_close,
                    period=self.p.slow_period,
                )
                for data in self.datas
            }

        def next(self) -> None:
            if _has_pending_order(self):
                return
            for data in self.datas:
                position = self.getposition(data)
                bullish = self.fast[data][0] > self.slow[data][0]
                bearish = self.fast[data][0] < self.slow[data][0]
                if not position and bullish:
                    self.order_target_percent(data=data, target=self.p.target_percent)
                elif position and bearish:
                    self.order_target_percent(data=data, target=0.0)

    return SignalSmaCrossStrategy
