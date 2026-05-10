from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

import pandas as pd

from quant_backtest.data.constants import Adjust, SOURCE_BAOSTOCK

VectorbtStrategyName = Literal[
    "sma-cross",
    "three-rising-hold-one",
    "three-falling-buy-three-rising-sell",
]


@dataclass(frozen=True)
class VectorbtConfig:
    symbols: list[str]
    strategy: VectorbtStrategyName
    start: str | None = None
    end: str | None = None
    cash: float = 1_000_000.0
    commission_bps: float = 3.0
    slippage_bps: float = 5.0
    size_granularity: float = 1.0
    source: str = SOURCE_BAOSTOCK
    signal_adjust: Adjust = "qfq"
    execution_adjust: Adjust = "raw"
    strategy_kwargs: Mapping[str, Any] = field(default_factory=dict)

    @property
    def commission_rate(self) -> float:
        return self.commission_bps / 10_000

    @property
    def slippage_rate(self) -> float:
        return self.slippage_bps / 10_000


@dataclass(frozen=True)
class VectorbtSignals:
    entries: pd.DataFrame
    exits: pd.DataFrame
    strategy: VectorbtStrategyName
    parameters: dict[str, Any]


@dataclass(frozen=True)
class VectorbtResult:
    metrics: pd.DataFrame
    entries: pd.DataFrame
    exits: pd.DataFrame
    close: pd.DataFrame
    portfolio: Any
    strategy: VectorbtStrategyName

    def ranked(self, by: str = "total_return", ascending: bool = False) -> pd.DataFrame:
        if by not in self.metrics.columns:
            raise KeyError(f"metric {by!r} is not available")
        return self.metrics.sort_values(by, ascending=ascending).reset_index(drop=True)
