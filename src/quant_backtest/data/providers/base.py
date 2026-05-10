from __future__ import annotations

from typing import Protocol

import pandas as pd

from quant_backtest.data.constants import Adjust


class MarketDataProvider(Protocol):
    def list_symbols(self, as_of: str | None = None) -> list[str]:
        ...

    def get_daily_bars(
        self,
        symbols: list[str],
        start: str,
        end: str,
        adjust: Adjust,
    ) -> pd.DataFrame:
        ...


class AkshareProvider:
    def list_symbols(self, as_of: str | None = None) -> list[str]:
        raise NotImplementedError("AkShare provider is reserved for a later version")

    def get_daily_bars(
        self,
        symbols: list[str],
        start: str,
        end: str,
        adjust: Adjust,
    ) -> pd.DataFrame:
        raise NotImplementedError("AkShare provider is reserved for a later version")


class TushareProvider:
    def list_symbols(self, as_of: str | None = None) -> list[str]:
        raise NotImplementedError("Tushare provider is reserved for a later version")

    def get_daily_bars(
        self,
        symbols: list[str],
        start: str,
        end: str,
        adjust: Adjust,
    ) -> pd.DataFrame:
        raise NotImplementedError("Tushare provider is reserved for a later version")
