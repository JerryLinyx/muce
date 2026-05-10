from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

import pandas as pd

from quant_backtest.data.constants import Adjust, SOURCE_BAOSTOCK

ExecutionTiming = Literal["next_open", "same_close"]


@dataclass(frozen=True)
class BacktraderConfig:
    symbols: list[str]
    start: str | None = None
    end: str | None = None
    cash: float = 1_000_000.0
    commission_bps: float = 3.0
    slippage_bps: float = 5.0
    source: str = SOURCE_BAOSTOCK
    signal_adjust: Adjust = "qfq"
    execution_adjust: Adjust = "raw"
    execution_timing: ExecutionTiming = "next_open"
    strategy_kwargs: Mapping[str, Any] = field(default_factory=dict)

    @property
    def commission_rate(self) -> float:
        return self.commission_bps / 10_000

    @property
    def slippage_rate(self) -> float:
        return self.slippage_bps / 10_000


@dataclass(frozen=True)
class BacktraderResult:
    metrics: dict[str, float | int | None]
    equity_curve: pd.DataFrame
    orders: pd.DataFrame
    trades: pd.DataFrame
    raw_analyzers: dict[str, Any]
    final_value: float
    start_cash: float

    def to_frames(self) -> dict[str, pd.DataFrame]:
        metrics = pd.DataFrame([self.metrics])
        return {
            "metrics": metrics,
            "equity_curve": self.equity_curve,
            "orders": self.orders,
            "trades": self.trades,
        }
