---
id: ADR-001
kind: decision
title: A-share Data Layer
date: 2026-05-07
status: accepted
---

# ADR 0001: A-share Data Layer

## Status

Accepted

## Context

The project needs a first-version data layer for A-share research and backtesting. It must support local repeatable backtests, avoid accidental mixed data semantics, and preserve a path toward realistic execution and paper trading.

Candidate data sources:

- `baostock`
- `akshare`
- `tushare`

Candidate storage models:

- Raw online API calls during backtests.
- Local CSV files.
- Local Parquet cache.
- DuckDB as primary storage.

## Decision

Use `baostock` as the first implemented data provider. Keep `akshare` and `tushare` as explicit provider boundaries with `NotImplementedError`.

Store data in local Parquet files partitioned by:

```text
source
adjust
symbol
```

Use this default cache root:

```text
data/cache/a_share/daily/
```

Store metadata in both the path and the Parquet file metadata:

- `source`
- `market`
- `frequency`
- `adjust`
- `calendar`

Use internal symbols:

```text
000001.SZ
600000.SH
```

Convert baostock symbols explicitly:

```text
000001.SZ <-> sz.000001
600000.SH <-> sh.600000
```

Do not silently normalize unsupported aliases such as `XSHE` and `XSHG` in v1.

## Reasoning

Backtests must be repeatable. Running directly against online APIs during research would make runs sensitive to network availability, upstream changes, and rate limits.

Parquet is a better v1 storage format than CSV because it preserves typed tabular data, supports metadata, and works well with pandas, pyarrow, and future DuckDB queries.

DuckDB is useful later as a query layer, but it should not replace the simple Parquet cache in v1. The current access pattern is mostly symbol-oriented: load several symbols over many years for sweep or validation. Symbol-partitioned Parquet is sufficient and easy to update incrementally.

Provider abstraction is necessary, but a generic `get_data()` interface would become ambiguous. The v1 provider interface is deliberately specific:

```python
get_daily_bars(symbols, start, end, adjust)
```

## Implementation

- `MarketDataProvider` protocol
- `BaostockProvider.get_daily_bars()` — first implemented provider
- `AkshareProvider` and `TushareProvider` stubs with `NotImplementedError`
- `to_internal_symbol()` / `to_vendor_symbol()` — `000001.SZ` ↔ `sz.000001`
- `ParquetCache` partitioned by `source/adjust/symbol` under `data/cache/a_share/daily/`
- Data quality validation: missing OHLCV, duplicates, date gaps
- vectorbt adapter for wide-panel loads
- backtrader adapter for per-symbol feeds
- CLI: `quant-data download`, `quant-data update`, `quant-data inspect`

## Consequences

Positive:

- Data source, market, frequency, and adjustment mode are explicit.
- Cache mixing is blocked by metadata checks.
- Future providers can be added behind the same daily bar interface.
- DuckDB can be added later without migrating the underlying cache.

Tradeoffs:

- v1 is daily A-share only.
- No automatic fallback between providers.
- No full-market date-partitioned panel yet.
- Cross-sectional factor workflows may need an additional query layer later.

## Follow-Up Work

- Add `DuckDBReader` over existing Parquet partitions.
- Add `AkshareProvider` only after clear field and adjustment mapping tests exist.
- Add `TushareProvider` only after token, permission, and rate-limit behavior is configured.
- Add integration tests for real baostock downloads behind an optional marker.

## Verification

`uv run pytest` — 19 passed (after backtrader module).
