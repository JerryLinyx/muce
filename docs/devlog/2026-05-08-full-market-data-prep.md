# 2026-05-08 Full-Market Data Preparation

## Prompt Context

The selector should eventually backtest over the past three years of full-market A-share data. This requires local storage of broad qfq/raw daily history before selector results are meaningful.

## Implementation

Extended `quant-data` with universe and full-market batch download support.

New command:

```bash
uv run quant-data universe --source baostock --as-of 20260507
```

Enhanced commands:

```bash
uv run quant-data download \
  --source baostock \
  --all-symbols \
  --as-of 20260507 \
  --start 20230508 \
  --end 20260507 \
  --adjust both \
  --batch-size 200
```

```bash
uv run quant-data update \
  --source baostock \
  --all-symbols \
  --as-of 20260507 \
  --start 20230508 \
  --end 20260507 \
  --adjust both \
  --batch-size 200
```

`--adjust both` downloads both:

```text
qfq for signals/features
raw for execution
```

Universe symbols are filtered to common A-share stock code ranges:

```text
SH: 600, 601, 603, 605, 688, 689
SZ: 000, 001, 002, 003, 300, 301
```

Indexes such as `sh.000001` are deliberately excluded.

## Query Layer Decision

We do not need a database server for v1. Parquet remains the source of truth.

Added optional DuckDB query support:

```toml
query = ["duckdb>=1.2"]
```

Added:

```text
src/quant_backtest/data/duckdb_reader.py
tests/test_duckdb_reader.py
```

DuckDB can query the existing Parquet cache directly without copying data into a database.

## Storage Estimate

Rough shape for three years:

```text
~5,000 stocks
~730 trading days
2 adjustment modes: qfq + raw
~7.3 million rows
```

Based on the current Parquet footprint for one symbol, expected storage is likely in the hundreds of MB to low single-digit GB range. Small-file overhead and metadata can push it higher, but this is still appropriate for local Parquet.

## Tests

Added/updated tests for:

- `quant-data universe`
- `quant-data download --all-symbols --adjust both`
- Optional DuckDB reader

Verification:

```bash
uv run pytest tests/test_cli.py tests/test_duckdb_reader.py
```

Result:

```text
4 passed, 1 skipped
```

DuckDB test is skipped unless the optional query extra is installed.

## Next Steps

- Run the full-market download outside normal unit tests because it requires network and will take time.
- Add resume/retry logging around failed symbols.
- Add a sector-basket pilot before full-market download if data provider throttling becomes an issue.
- Use DuckDBReader for full-market data health checks after the cache is populated.

## One-Year Full-Market Download Result

Started a one-year full-market download:

```bash
uv run quant-data download \
  --source baostock \
  --all-symbols \
  --as-of 20260507 \
  --start 20250507 \
  --end 20260507 \
  --adjust both \
  --batch-size 100
```

Result:

```text
symbol_count: 5200
qfq rows: 1,253,051
raw rows: 1,253,051
total rows: 2,506,102
cache size: 245M
```

Final cache shape:

```text
qfq parquet files: 5200
raw parquet files: 5200
date range: 2025-05-07 to 2026-05-07
```

Quality inspection:

```text
missing OHLC: 0
duplicate rows: 0
suspended rows: 2405
ST rows: 41339
```

Warnings:

```text
trade_status contains suspended rows
is_st contains ST rows
date gaps detected within one or more symbols
large close-to-close price jumps detected
```

Interpretation:

- Suspended and ST rows are expected in full-market A-share data and should be filtered by selectors/backtests when needed.
- Date-gap warnings are expected until a real exchange calendar validator replaces the current simple gap heuristic.
- Large close-to-close jumps need later review; some may be real events, some may come from raw/qfq corporate action behavior or data issues.

Follow-up implementation:

- `quant-data download/update` output was changed to report symbol counts and samples rather than printing every symbol, because the full-market JSON output was too large.
