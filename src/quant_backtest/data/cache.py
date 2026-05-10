from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from quant_backtest.data.constants import (
    Adjust,
    CALENDAR_CN_A_SHARE,
    FREQUENCY_DAILY,
    MARKET_CN_A_SHARE,
    SOURCE_BAOSTOCK,
)
from quant_backtest.data.schema import QualityReport, normalize_daily_bars, validate_daily_bars
from quant_backtest.data.symbols import validate_internal_symbol

METADATA_KEYS = ["source", "market", "frequency", "adjust", "calendar"]


@dataclass
class CacheInspection:
    source: str
    adjust: str
    frequency: str
    symbol_count: int
    date_start: str | None
    date_end: str | None
    row_count: int
    missing_ohlc_count: int
    duplicate_count: int
    suspended_rows: int
    st_rows: int
    last_update_time: str | None
    warnings: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "adjust": self.adjust,
            "frequency": self.frequency,
            "symbol_count": self.symbol_count,
            "date_range": [self.date_start, self.date_end],
            "row_count": self.row_count,
            "missing_ohlc_count": self.missing_ohlc_count,
            "duplicate_count": self.duplicate_count,
            "suspended_rows": self.suspended_rows,
            "st_rows": self.st_rows,
            "last_update_time": self.last_update_time,
            "warnings": self.warnings,
        }


class ParquetCache:
    def __init__(self, root: str | Path = "data/cache/a_share/daily") -> None:
        self.root = Path(root)

    def write(self, df: pd.DataFrame) -> None:
        data = normalize_daily_bars(df)
        validate_daily_bars(data)

        for (source, adjust, symbol), group in data.groupby(["source", "adjust", "symbol"], sort=False):
            symbol = validate_internal_symbol(str(symbol))
            metadata = _metadata_from_frame(group)
            path = self._path(str(source), str(adjust), symbol)
            path.parent.mkdir(parents=True, exist_ok=True)
            output = group.reset_index(drop=True)
            if path.exists():
                existing, existing_metadata = _read_parquet(path)
                _assert_metadata({key: metadata[key] for key in METADATA_KEYS}, existing_metadata)
                output = (
                    pd.concat([existing, output], ignore_index=True)
                    .pipe(normalize_daily_bars)
                    .drop_duplicates(["date", "symbol"], keep="last")
                    .sort_values(["symbol", "date"])
                    .reset_index(drop=True)
                )
                validate_daily_bars(output)
            _write_parquet(output, path, metadata)

    def read_symbol(
        self,
        *,
        source: str = SOURCE_BAOSTOCK,
        adjust: Adjust = "qfq",
        symbol: str,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        symbol = validate_internal_symbol(symbol)
        path = self._path(source, adjust, symbol)
        if not path.exists():
            raise FileNotFoundError(f"cache file does not exist: {path}")
        data, metadata = _read_parquet(path)
        expected = {
            "source": source,
            "market": MARKET_CN_A_SHARE,
            "frequency": FREQUENCY_DAILY,
            "adjust": adjust,
            "calendar": CALENDAR_CN_A_SHARE,
        }
        _assert_metadata(expected, metadata)
        data = normalize_daily_bars(data)
        validate_daily_bars(data, expected_metadata=expected)
        data = data[data["symbol"].eq(symbol)]
        if start:
            data = data[data["date"].ge(pd.to_datetime(start))]
        if end:
            data = data[data["date"].le(pd.to_datetime(end))]
        return data.reset_index(drop=True)

    def read_many(
        self,
        *,
        source: str = SOURCE_BAOSTOCK,
        adjust: Adjust = "qfq",
        symbols: Iterable[str],
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        frames = [
            self.read_symbol(source=source, adjust=adjust, symbol=symbol, start=start, end=end)
            for symbol in symbols
        ]
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def last_date(
        self,
        *,
        source: str = SOURCE_BAOSTOCK,
        adjust: Adjust = "qfq",
        symbol: str,
    ) -> pd.Timestamp | None:
        try:
            data = self.read_symbol(source=source, adjust=adjust, symbol=symbol)
        except FileNotFoundError:
            return None
        if data.empty:
            return None
        return data["date"].max()

    def inspect(
        self,
        *,
        source: str = SOURCE_BAOSTOCK,
        adjust: Adjust = "qfq",
        symbols: Iterable[str] | None = None,
    ) -> CacheInspection:
        selected = list(symbols or self.available_symbols(source=source, adjust=adjust))
        frames = []
        warnings: list[str] = []
        for symbol in selected:
            try:
                frames.append(self.read_symbol(source=source, adjust=adjust, symbol=symbol))
            except FileNotFoundError as exc:
                warnings.append(str(exc))
        if not frames:
            return CacheInspection(source, adjust, FREQUENCY_DAILY, 0, None, None, 0, 0, 0, 0, 0, None, warnings)

        data = pd.concat(frames, ignore_index=True)
        report = validate_daily_bars(data, raise_on_error=False)
        warnings.extend(report.warnings)
        return _inspection_from_data(data, source=source, adjust=adjust, report=report)

    def available_symbols(self, *, source: str = SOURCE_BAOSTOCK, adjust: Adjust = "qfq") -> list[str]:
        base = self.root / f"source={source}" / f"adjust={adjust}"
        if not base.exists():
            return []
        return sorted(path.name.removeprefix("symbol=") for path in base.glob("symbol=*") if path.is_dir())

    def _path(self, source: str, adjust: str, symbol: str) -> Path:
        return self.root / f"source={source}" / f"adjust={adjust}" / f"symbol={symbol}" / "part.parquet"


def _metadata_from_frame(df: pd.DataFrame) -> dict[str, str]:
    metadata = {}
    for key in METADATA_KEYS:
        values = set(df[key].dropna().astype(str))
        if len(values) != 1:
            raise ValueError(f"cannot write cache with multiple {key} values: {sorted(values)!r}")
        metadata[key] = next(iter(values))
    metadata["last_update_time"] = datetime.now(timezone.utc).isoformat()
    return metadata


def _write_parquet(df: pd.DataFrame, path: Path, metadata: Mapping[str, str]) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.Table.from_pandas(df, preserve_index=False)
    existing = table.schema.metadata or {}
    merged = dict(existing)
    merged.update({key.encode(): value.encode() for key, value in metadata.items()})
    table = table.replace_schema_metadata(merged)
    pq.write_table(table, path)


def _read_parquet(path: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    import pyarrow.parquet as pq

    table = pq.ParquetFile(path).read()
    metadata = {
        key.decode(): value.decode()
        for key, value in (table.schema.metadata or {}).items()
        if key.decode() in {*METADATA_KEYS, "last_update_time"}
    }
    return table.to_pandas(), metadata


def _assert_metadata(expected: Mapping[str, str], actual: Mapping[str, str]) -> None:
    mismatches = []
    for key, value in expected.items():
        if actual.get(key) != value:
            mismatches.append(f"{key}: expected {value!r}, got {actual.get(key)!r}")
    if mismatches:
        raise ValueError("cache metadata mismatch: " + "; ".join(mismatches))


def _inspection_from_data(
    data: pd.DataFrame,
    *,
    source: str,
    adjust: str,
    report: QualityReport,
) -> CacheInspection:
    missing_ohlc = data[["open", "high", "low", "close"]].isna().any(axis=1).sum()
    duplicates = data.duplicated(["date", "symbol"]).sum()
    last_update = data["query_time"].dropna().astype(str).max() if not data.empty else None
    return CacheInspection(
        source=source,
        adjust=adjust,
        frequency=FREQUENCY_DAILY,
        symbol_count=int(data["symbol"].nunique()),
        date_start=data["date"].min().date().isoformat() if not data.empty else None,
        date_end=data["date"].max().date().isoformat() if not data.empty else None,
        row_count=len(data),
        missing_ohlc_count=int(missing_ohlc),
        duplicate_count=int(duplicates),
        suspended_rows=int(data["trade_status"].eq(0).sum()),
        st_rows=int(data["is_st"].eq(1).sum()),
        last_update_time=last_update,
        warnings=report.warnings,
    )
