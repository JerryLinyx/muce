from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

import pandas as pd

from quant_backtest.data.adapters import (
    DEFAULT_VECTORBT_FIELDS,
    load_backtrader_frame,
    load_for_vectorbt,
)
from quant_backtest.backtest.backtrader_engine import BacktraderEngine
from quant_backtest.backtest.models import BacktraderConfig, BacktraderResult, ExecutionTiming
from quant_backtest.backtest.vectorbt_engine import VectorbtEngine
from quant_backtest.backtest.vectorbt_models import VectorbtConfig, VectorbtResult, VectorbtStrategyName
from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import Adjust, SOURCE_BAOSTOCK


@dataclass
class VectorbtRunner:
    cache: ParquetCache
    source: str = SOURCE_BAOSTOCK
    signal_adjust: Adjust = "qfq"
    execution_adjust: Adjust = "raw"

    def load_price_panels(
        self,
        symbols: Iterable[str],
        *,
        fields: Iterable[str] = DEFAULT_VECTORBT_FIELDS,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, pd.DataFrame]:
        return load_for_vectorbt(
            self.cache,
            symbols,
            fields=fields,
            start=start,
            end=end,
            source=self.source,
            adjust=self.signal_adjust,
        )

    def run_from_signals(
        self,
        close: pd.DataFrame,
        entries: pd.DataFrame,
        exits: pd.DataFrame,
        **kwargs: Any,
    ) -> Any:
        try:
            import vectorbt as vbt
        except ImportError as exc:
            raise RuntimeError(
                "vectorbt is required for vectorized sweeps; install with quant-backtest[research]"
            ) from exc
        return vbt.Portfolio.from_signals(close, entries, exits, **kwargs)

    def run(
        self,
        *,
        strategy: VectorbtStrategyName,
        symbols: Iterable[str],
        start: str | None = None,
        end: str | None = None,
        cash: float = 1_000_000,
        commission_bps: float = 3.0,
        slippage_bps: float = 5.0,
        strategy_kwargs: Mapping[str, Any] | None = None,
    ) -> VectorbtResult:
        config = VectorbtConfig(
            symbols=list(symbols),
            strategy=strategy,
            start=start,
            end=end,
            cash=cash,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            source=self.source,
            signal_adjust=self.signal_adjust,
            execution_adjust=self.execution_adjust,
            strategy_kwargs=dict(strategy_kwargs or {}),
        )
        return VectorbtEngine(self.cache).run(config)

    def sweep(
        self,
        *,
        strategy: VectorbtStrategyName,
        symbols: Iterable[str],
        parameter_grid: Mapping[str, list[Any]],
        start: str | None = None,
        end: str | None = None,
        cash: float = 1_000_000,
        commission_bps: float = 3.0,
        slippage_bps: float = 5.0,
        strategy_kwargs: Mapping[str, Any] | None = None,
    ) -> VectorbtResult:
        config = VectorbtConfig(
            symbols=list(symbols),
            strategy=strategy,
            start=start,
            end=end,
            cash=cash,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            source=self.source,
            signal_adjust=self.signal_adjust,
            execution_adjust=self.execution_adjust,
            strategy_kwargs=dict(strategy_kwargs or {}),
        )
        return VectorbtEngine(self.cache).sweep(config, parameter_grid)


@dataclass
class BacktraderRunner:
    cache: ParquetCache
    source: str = SOURCE_BAOSTOCK
    signal_adjust: Adjust = "qfq"
    execution_adjust: Adjust = "raw"
    execution_timing: ExecutionTiming = "next_open"

    def load_signal_data(
        self,
        symbols: Iterable[str],
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, pd.DataFrame]:
        return load_for_vectorbt(
            self.cache,
            symbols,
            start=start,
            end=end,
            source=self.source,
            adjust=self.signal_adjust,
        )

    def load_execution_frame(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        return load_backtrader_frame(
            self.cache,
            symbol,
            start=start,
            end=end,
            source=self.source,
            price_mode=self.execution_adjust,
        )

    def run(
        self,
        strategy_factory: Callable[..., Any],
        symbols: Iterable[str],
        *,
        start: str | None = None,
        end: str | None = None,
        cash: float = 1_000_000,
        commission: float = 0.0003,
        slippage_perc: float = 0.0005,
        strategy_kwargs: Mapping[str, Any] | None = None,
    ) -> BacktraderResult:
        config = BacktraderConfig(
            symbols=list(symbols),
            start=start,
            end=end,
            cash=cash,
            commission_bps=commission * 10_000,
            slippage_bps=slippage_perc * 10_000,
            source=self.source,
            signal_adjust=self.signal_adjust,
            execution_adjust=self.execution_adjust,
            execution_timing=self.execution_timing,
            strategy_kwargs=dict(strategy_kwargs or {}),
        )
        return BacktraderEngine(self.cache).run(strategy_factory, config)
