from __future__ import annotations

import pandas as pd
import pytest

from quant_backtest.data.cache import ParquetCache
from quant_backtest.services import data_service
from tests.conftest import make_bars


@pytest.fixture()
def cache_with_symbols(tmp_path) -> ParquetCache:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=3, start="2026-05-07"))
    cache.write(make_bars("600000.SH", adjust="qfq", rows=2, start="2026-05-08"))
    return cache


def test_list_symbols_returns_all(cache_with_symbols):
    rows = data_service.list_symbols(cache_with_symbols, adjust="qfq")
    assert {row.symbol for row in rows} == {"000001.SZ", "600000.SH"}


def test_list_symbols_filters_by_market(cache_with_symbols):
    rows = data_service.list_symbols(cache_with_symbols, adjust="qfq", market="SZ")
    assert [row.symbol for row in rows] == ["000001.SZ"]


def test_list_symbols_query_prefix(cache_with_symbols):
    rows = data_service.list_symbols(cache_with_symbols, adjust="qfq", query="000")
    assert [row.symbol for row in rows] == ["000001.SZ"]


def test_symbol_info_returns_latest_date(cache_with_symbols):
    info = data_service.symbol_info(cache_with_symbols, "000001.SZ", adjust="qfq")
    assert info.symbol == "000001.SZ"
    assert info.market == "SZ"
    assert info.last_cached_date is not None
    # rows=3 starting 2026-05-07 with bdate_range gives 5/7, 5/8, 5/11 (Mon)
    # Using bdate_range from pandas.
    dates = pd.bdate_range("2026-05-07", periods=3)
    assert pd.Timestamp(info.last_cached_date) == dates[-1]


def test_load_bars_returns_rows(cache_with_symbols):
    result = data_service.load_bars_with_indicators(
        cache_with_symbols, "000001.SZ", adjust="qfq", indicators=()
    )
    assert result.symbol == "000001.SZ"
    assert result.adjust == "qfq"
    assert len(result.rows) == 3
    first = result.rows[0]
    expected_first = pd.bdate_range("2026-05-07", periods=3)[0].strftime("%Y-%m-%d")
    assert first["date"] == expected_first
    assert first["open"] == pytest.approx(9.8)


def test_load_bars_with_indicators(cache_with_symbols):
    # Add a longer panel so MA can warm up.
    long_cache = cache_with_symbols
    long_cache.write(make_bars("300999.SZ", adjust="qfq", rows=10, start="2026-04-01"))
    result = data_service.load_bars_with_indicators(
        long_cache, "300999.SZ", adjust="qfq", indicators=("ma_5",)
    )
    assert "ma_5" in result.rows[-1]
    last = result.rows[-1]["ma_5"]
    # closes are 10..19 (rows=10), MA_5 of last 5 closes = (15+16+17+18+19)/5 = 17
    assert last == pytest.approx(17.0)


def test_cache_coverage(cache_with_symbols):
    coverage = data_service.cache_coverage(cache_with_symbols, adjust="qfq")
    by_symbol = {entry.symbol: entry for entry in coverage}
    assert by_symbol["000001.SZ"].rows == 3
    assert by_symbol["600000.SH"].rows == 2
    expected_first = pd.bdate_range("2026-05-07", periods=3)[0].date()
    assert by_symbol["000001.SZ"].first_date == expected_first
