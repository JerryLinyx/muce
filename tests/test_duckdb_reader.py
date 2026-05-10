from __future__ import annotations

import pytest

from quant_backtest.data import DuckDBReader, ParquetCache, duckdb_available
from tests.conftest import make_bars


pytestmark = pytest.mark.skipif(not duckdb_available(), reason="DuckDB optional extra is not installed")


def test_duckdb_reader_queries_parquet_cache(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=3))
    cache.write(make_bars("600000.SH", adjust="qfq", rows=3))

    reader = DuckDBReader(tmp_path)
    data = reader.daily_bars(
        adjust="qfq",
        symbols=["000001.SZ"],
        columns=["date", "symbol", "close"],
    )
    inspection = reader.inspect(adjust="qfq")

    assert list(data["symbol"].unique()) == ["000001.SZ"]
    assert len(data) == 3
    assert inspection["row_count"] == 6
    assert inspection["symbol_count"] == 2
