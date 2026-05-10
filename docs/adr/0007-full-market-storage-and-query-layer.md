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

Added:

```text
src/quant_backtest/data/duckdb_reader.py
tests/test_duckdb_reader.py
```

The reader provides:

```python
DuckDBReader.daily_bars(...)
DuckDBReader.inspect(...)
```

Tests are skipped when the optional `query` extra is not installed.

## Consequences

- Use `uv sync --extra query` before using `DuckDBReader`.
- Keep writes through `ParquetCache`.
- Use DuckDB only for SQL reads and summaries.
- Reconsider a database server only if we add minute/tick data, a factor store with many versions, concurrent ingestion, or live service APIs.
