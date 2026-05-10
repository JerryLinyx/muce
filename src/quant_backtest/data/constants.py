from __future__ import annotations

from typing import Literal

Adjust = Literal["raw", "qfq", "hfq"]

SOURCE_BAOSTOCK = "baostock"
MARKET_CN_A_SHARE = "cn_a_share"
FREQUENCY_DAILY = "1d"
CALENDAR_CN_A_SHARE = "cn_sse_szse"
CURRENCY_CNY = "CNY"

INTERNAL_ADJUST_TO_BAOSTOCK: dict[Adjust, str] = {
    "hfq": "1",
    "qfq": "2",
    "raw": "3",
}

BAOSTOCK_ADJUST_TO_INTERNAL = {
    value: key for key, value in INTERNAL_ADJUST_TO_BAOSTOCK.items()
}

STANDARD_DAILY_COLUMNS = [
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "volume",
    "amount",
    "adjust",
    "source",
    "market",
    "frequency",
    "calendar",
    "query_time",
    "currency",
    "trade_status",
    "is_st",
]

OHLC_COLUMNS = ["open", "high", "low", "close"]
