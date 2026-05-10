from __future__ import annotations

import pytest

from quant_backtest.data.adapters import (
    load_backtrader_frame,
    load_backtrader_signal_execution_frame,
    load_for_vectorbt,
)
from quant_backtest.data.cache import ParquetCache, _read_parquet, _write_parquet
from quant_backtest.data.constants import (
    CALENDAR_CN_A_SHARE,
    FREQUENCY_DAILY,
    MARKET_CN_A_SHARE,
    SOURCE_BAOSTOCK,
)
from tests.conftest import make_bars


def test_cache_writes_symbol_partition_and_reads_metadata(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq"))

    expected_path = (
        tmp_path
        / "source=baostock"
        / "adjust=qfq"
        / "symbol=000001.SZ"
        / "part.parquet"
    )
    assert expected_path.exists()

    data = cache.read_symbol(symbol="000001.SZ", adjust="qfq")
    assert list(data["symbol"].unique()) == ["000001.SZ"]
    _, metadata = _read_parquet(expected_path)
    assert metadata["source"] == SOURCE_BAOSTOCK
    assert metadata["market"] == MARKET_CN_A_SHARE
    assert metadata["frequency"] == FREQUENCY_DAILY
    assert metadata["adjust"] == "qfq"
    assert metadata["calendar"] == CALENDAR_CN_A_SHARE


def test_cache_rejects_metadata_mismatch(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    data = make_bars("000001.SZ", adjust="qfq")
    path = tmp_path / "source=baostock" / "adjust=qfq" / "symbol=000001.SZ" / "part.parquet"
    path.parent.mkdir(parents=True)
    _write_parquet(
        data,
        path,
        {
            "source": SOURCE_BAOSTOCK,
            "market": MARKET_CN_A_SHARE,
            "frequency": FREQUENCY_DAILY,
            "adjust": "raw",
            "calendar": CALENDAR_CN_A_SHARE,
        },
    )

    with pytest.raises(ValueError, match="cache metadata mismatch"):
        cache.read_symbol(symbol="000001.SZ", adjust="qfq")


def test_cache_write_merges_incremental_rows(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    first = make_bars("000001.SZ", rows=2, start="2024-01-02")
    second = make_bars("000001.SZ", rows=2, start="2024-01-04")
    cache.write(first)
    cache.write(second)

    data = cache.read_symbol(symbol="000001.SZ")
    assert len(data) == 4
    assert data["date"].is_monotonic_increasing


def test_vectorbt_adapter_returns_wide_field_panels(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq"))
    cache.write(make_bars("600000.SH", adjust="qfq"))

    panels = load_for_vectorbt(cache, ["000001.SZ", "600000.SH"], adjust="qfq")
    assert set(panels) == {"open", "high", "low", "close", "volume"}
    assert list(panels["close"].columns) == ["000001.SZ", "600000.SH"]
    assert len(panels["close"]) == 3


def test_backtrader_frame_uses_raw_execution_prices(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("000001.SZ", adjust="qfq")
    raw = make_bars("000001.SZ", adjust="raw")
    raw["close"] = raw["close"] + 100
    cache.write(qfq)
    cache.write(raw)

    frame = load_backtrader_frame(cache, "000001.SZ", price_mode="raw")
    assert list(frame.columns) == ["open", "high", "low", "close", "volume", "openinterest"]
    assert frame["close"].iloc[0] == pytest.approx(110.0)


def test_backtrader_signal_execution_frame_keeps_raw_and_qfq_prices(tmp_path) -> None:
    cache = ParquetCache(tmp_path)
    qfq = make_bars("000001.SZ", adjust="qfq")
    raw = make_bars("000001.SZ", adjust="raw")
    raw["close"] = raw["close"] + 100
    qfq["close"] = qfq["close"] + 10
    cache.write(qfq)
    cache.write(raw)

    frame = load_backtrader_signal_execution_frame(cache, "000001.SZ")
    assert frame["close"].iloc[0] == pytest.approx(110.0)
    assert frame["signal_close"].iloc[0] == pytest.approx(20.0)
    assert "signal_volume" in frame.columns
