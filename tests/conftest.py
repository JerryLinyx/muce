from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from quant_backtest.data.constants import (
    CALENDAR_CN_A_SHARE,
    CURRENCY_CNY,
    FREQUENCY_DAILY,
    MARKET_CN_A_SHARE,
    SOURCE_BAOSTOCK,
)


def make_bars(
    symbol: str = "000001.SZ",
    *,
    adjust: str = "qfq",
    source: str = SOURCE_BAOSTOCK,
    rows: int = 3,
    start: str = "2024-01-02",
    trade_status: int = 1,
    is_st: int = 0,
) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=rows)
    query_time = datetime.now(timezone.utc).isoformat()
    records = []
    for idx, date in enumerate(dates):
        close = 10.0 + idx
        records.append(
            {
                "date": date,
                "symbol": symbol,
                "open": close - 0.2,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "pre_close": close - 1,
                "volume": 1000 + idx,
                "amount": (1000 + idx) * close,
                "adjust": adjust,
                "source": source,
                "market": MARKET_CN_A_SHARE,
                "frequency": FREQUENCY_DAILY,
                "calendar": CALENDAR_CN_A_SHARE,
                "query_time": query_time,
                "currency": CURRENCY_CNY,
                "trade_status": trade_status,
                "is_st": is_st,
            }
        )
    return pd.DataFrame(records)
