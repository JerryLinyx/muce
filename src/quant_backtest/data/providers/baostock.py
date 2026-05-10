from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from quant_backtest.data.constants import (
    CALENDAR_CN_A_SHARE,
    CURRENCY_CNY,
    FREQUENCY_DAILY,
    INTERNAL_ADJUST_TO_BAOSTOCK,
    MARKET_CN_A_SHARE,
    SOURCE_BAOSTOCK,
    Adjust,
)
from quant_backtest.data.schema import normalize_daily_bars, validate_daily_bars
from quant_backtest.data.symbols import to_internal_symbol, to_vendor_symbol, validate_internal_symbol

BAOSTOCK_FIELDS = ",".join(
    [
        "date",
        "code",
        "open",
        "high",
        "low",
        "close",
        "preclose",
        "volume",
        "amount",
        "adjustflag",
        "tradestatus",
        "isST",
    ]
)


@dataclass
class BaostockProvider:
    source: str = SOURCE_BAOSTOCK

    def list_symbols(self, as_of: str | None = None) -> list[str]:
        try:
            import baostock as bs
        except ImportError as exc:
            raise RuntimeError(
                "baostock is required for BaostockProvider; install with quant-backtest[data]"
            ) from exc

        login = bs.login()
        if login.error_code != "0":
            raise RuntimeError(f"baostock login failed: {login.error_msg}")
        try:
            result = bs.query_all_stock(day=_format_baostock_date(as_of) if as_of else None)
            if result.error_code != "0":
                raise RuntimeError(f"baostock universe query failed: {result.error_msg}")
            rows = []
            while result.next():
                rows.append(result.get_row_data())
            if not rows:
                return []
            raw = pd.DataFrame(rows, columns=result.fields)
            return sorted(
                {
                    to_internal_symbol(code, SOURCE_BAOSTOCK)
                    for code in raw["code"].astype(str)
                    if _is_supported_a_share_stock(code)
                }
            )
        finally:
            bs.logout()

    def get_daily_bars(
        self,
        symbols: list[str],
        start: str,
        end: str,
        adjust: Adjust,
    ) -> pd.DataFrame:
        try:
            import baostock as bs
        except ImportError as exc:
            raise RuntimeError(
                "baostock is required for BaostockProvider; install with quant-backtest[data]"
            ) from exc

        adjustflag = INTERNAL_ADJUST_TO_BAOSTOCK[adjust]
        query_time = datetime.now(timezone.utc).isoformat()
        frames: list[pd.DataFrame] = []

        login = bs.login()
        if login.error_code != "0":
            raise RuntimeError(f"baostock login failed: {login.error_msg}")
        try:
            for symbol in symbols:
                internal_symbol = validate_internal_symbol(symbol)
                vendor_symbol = to_vendor_symbol(internal_symbol, SOURCE_BAOSTOCK)
                result = bs.query_history_k_data_plus(
                    vendor_symbol,
                    BAOSTOCK_FIELDS,
                    start_date=_format_baostock_date(start),
                    end_date=_format_baostock_date(end),
                    frequency="d",
                    adjustflag=adjustflag,
                )
                if result.error_code != "0":
                    raise RuntimeError(
                        f"baostock query failed for {internal_symbol}: {result.error_msg}"
                    )

                rows = []
                while result.next():
                    rows.append(result.get_row_data())
                if rows:
                    raw = pd.DataFrame(rows, columns=result.fields)
                    frames.append(_map_baostock_frame(raw, adjust=adjust, query_time=query_time))
        finally:
            bs.logout()

        if not frames:
            return normalize_daily_bars(pd.DataFrame(columns=_standard_columns()))

        data = pd.concat(frames, ignore_index=True)
        data = normalize_daily_bars(data)
        validate_daily_bars(data)
        return data


def _map_baostock_frame(df: pd.DataFrame, *, adjust: Adjust, query_time: str) -> pd.DataFrame:
    mapped = pd.DataFrame(
        {
            "date": df["date"],
            "symbol": df["code"].map(lambda value: to_internal_symbol(value, SOURCE_BAOSTOCK)),
            "open": df["open"],
            "high": df["high"],
            "low": df["low"],
            "close": df["close"],
            "pre_close": df["preclose"],
            "volume": df["volume"],
            "amount": df["amount"],
            "adjust": adjust,
            "source": SOURCE_BAOSTOCK,
            "market": MARKET_CN_A_SHARE,
            "frequency": FREQUENCY_DAILY,
            "calendar": CALENDAR_CN_A_SHARE,
            "query_time": query_time,
            "currency": CURRENCY_CNY,
            "trade_status": df["tradestatus"],
            "is_st": df["isST"],
        }
    )
    return mapped


def _format_baostock_date(value: str) -> str:
    value = value.strip()
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return value


def _is_supported_a_share_stock(vendor_code: str) -> bool:
    value = vendor_code.strip().lower()
    if not value.startswith(("sh.", "sz.")):
        return False
    code = value.split(".", maxsplit=1)[1]
    if len(code) != 6 or not code.isdigit():
        return False
    if value.startswith("sh."):
        return code.startswith(("600", "601", "603", "605", "688", "689"))
    return code.startswith(("000", "001", "002", "003", "300", "301"))


def _standard_columns() -> list[str]:
    from quant_backtest.data.constants import STANDARD_DAILY_COLUMNS

    return STANDARD_DAILY_COLUMNS
