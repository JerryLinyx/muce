from __future__ import annotations

from typing import Any

import pandas as pd


def get_ashare_pandas_data_class() -> Any:
    try:
        import backtrader as bt
    except ImportError as exc:
        raise RuntimeError(
            "backtrader is required for ASharePandasData; install with quant-backtest[validation]"
        ) from exc

    class ASharePandasData(bt.feeds.PandasData):
        lines = (
            "pre_close",
            "amount",
            "trade_status",
            "is_st",
            "signal_open",
            "signal_high",
            "signal_low",
            "signal_close",
            "signal_volume",
        )
        params = (
            ("datetime", None),
            ("open", "open"),
            ("high", "high"),
            ("low", "low"),
            ("close", "close"),
            ("volume", "volume"),
            ("openinterest", "openinterest"),
            ("pre_close", "pre_close"),
            ("amount", "amount"),
            ("trade_status", "trade_status"),
            ("is_st", "is_st"),
            ("signal_open", "signal_open"),
            ("signal_high", "signal_high"),
            ("signal_low", "signal_low"),
            ("signal_close", "signal_close"),
            ("signal_volume", "signal_volume"),
        )

    return ASharePandasData


def make_ashare_feed(frame: pd.DataFrame, *, name: str) -> Any:
    feed_class = get_ashare_pandas_data_class()
    return feed_class(dataname=frame, name=name)
