---
id: ADR-007
kind: decision
title: Full-Market Storage And Query Layer
date: 2026-05-08
status: accepted
---

# ADR 0007: Full-Market Storage And Query Layer

## Status

Accepted

## Context

Daily selector research requires multiple years of A-share history across a broad universe. For a three-year full-market cache, the project needs to store millions of rows across qfq signal data and raw execution data.

The question is whether this requires a database.

## Decision

Keep Parquet as the source of truth for v1.

Add DuckDB as an optional query layer:

```toml
query = ["duckdb>=1.2"]
```

Parquet remains the persisted storage format:

```text
data/cache/a_share/daily/
  source=baostock/
    adjust=qfq/
      symbol=000001.SZ/part.parquet
    adjust=raw/
      symbol=000001.SZ/part.parquet
```

DuckDB is used to query those Parquet files directly. It does not own the data and does not replace the cache.

## Rationale

- Three years of A-share daily OHLCV data is large enough to need efficient scans, but not large enough to require operating a database server.
- Parquet is simple, portable, compressible, and works well for backtesting and batch research.
- DuckDB can query partitioned Parquet directly with SQL, which is enough for daily selector scans, date filters, inspections, and data health checks.
- PostgreSQL or ClickHouse would add operational complexity before the project needs intraday data, tick data, concurrent writes, or multi-user serving.

## Implementation

One-year full-market download result:
- 5200 symbols, 2,506,102 rows (1,253,051 qfq + 1,253,051 raw), 245MB cache
- `quant-data universe` — list A-share symbols from baostock
- `quant-data download --all-symbols --adjust both --batch-size 100` — batch download
- `quant-data update --all-symbols --adjust both` — incremental update
- Universe symbols filtered to common stock code ranges (SH: 600/601/603/605/688/689, SZ: 000/001/002/003/300/301)

DuckDB reader: `DuckDBReader.daily_bars()` and `DuckDBReader.inspect()` over partitioned Parquet. Tests skipped when `query` extra is not installed.

Data quality inspection:
- Missing OHLCV: 0
- Duplicates: 0
- Suspended rows: 2405
- ST rows: 41339

## Consequences

- Use `uv sync --extra query` before using `DuckDBReader`.
- Keep writes through `ParquetCache`.
- Use DuckDB only for SQL reads and summaries.
- Reconsider a database server only if we add minute/tick data, a factor store with many versions, concurrent ingestion, or live service APIs.
