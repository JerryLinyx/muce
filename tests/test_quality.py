from __future__ import annotations

import pytest
import pandas as pd

from quant_backtest.data.schema import DataQualityError, validate_daily_bars
from tests.conftest import make_bars


def test_hard_error_for_duplicate_date_symbol() -> None:
    data = make_bars(rows=1)
    duplicate = data.copy()
    with pytest.raises(DataQualityError) as exc_info:
        validate_daily_bars(pd.concat([data, duplicate], ignore_index=True))
    assert "duplicate date + symbol" in str(exc_info.value)


def test_hard_error_for_non_positive_ohlc_on_trading_row() -> None:
    data = make_bars(rows=1)
    data.loc[0, "close"] = 0
    with pytest.raises(DataQualityError) as exc_info:
        validate_daily_bars(data)
    assert "non-positive OHLC" in str(exc_info.value)


def test_warning_checks_do_not_fail() -> None:
    data = make_bars(rows=2, trade_status=0, is_st=1)
    data.loc[0, "volume"] = 0
    data.loc[1, "amount"] = 0
    report = validate_daily_bars(data)
    assert report.ok
    assert "volume contains zero values" in report.warnings
    assert "amount contains zero values" in report.warnings
    assert "trade_status contains suspended rows" in report.warnings
    assert "is_st contains ST rows" in report.warnings
