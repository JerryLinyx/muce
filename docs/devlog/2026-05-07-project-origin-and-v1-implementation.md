# 2026-05-07 Project Origin And V1 Implementation

## Context

The project started as an empty workspace intended to become an A-share agent trading and quant research system. The first target was a backtesting foundation, with a data layer that can later support research sweeps, deeper validation, and eventually paper trading.

Initial project direction:

- Build a Python package plus CLI, managed by `uv`.
- Focus on A-share daily bars first.
- Use local cached data rather than direct online reads during backtests.
- Separate fast research sweeps from deeper event-driven validation.
- Preserve the path toward realistic execution by distinguishing signal prices from execution prices.

## Ideas Considered

### Build A Small Custom Core First

The first idea was to implement a small custom backtest core with pandas data structures. This would keep dependencies light and make the core behavior explicit.

Reasoning:

- The project was empty, so there was no existing framework constraint.
- Daily, long-only A-share research does not require a complex engine at the beginning.
- A small core would be easier to test and easier to adapt later.

This was useful as a baseline, but the direction changed after considering framework strengths.

### Use Both vectorbt And backtrader

The selected direction was to use both:

- `vectorbt` for fast parameter sweeps and research iteration.
- `backtrader` for deeper event-driven validation.

Reasoning:

- `vectorbt` is naturally aligned with pandas/NumPy wide panels and parameter grids.
- `backtrader` provides strategy classes, broker simulation, order execution, analyzers, and data feeds.
- The two frameworks solve different problems. Forcing one to do both would either reduce research speed or weaken validation fidelity.

Decision:

- Keep both as optional dependencies.
- Put shared behavior in data loading, cache, adapters, and normalized result objects.
- Avoid spreading direct framework-specific code through the rest of the project.

## Data Source Discussion

The first A-share data source decision considered:

- `baostock`
- `akshare`
- `tushare`

Selected v1 source:

- `baostock` as the implemented provider.
- `akshare` and `tushare` as reserved provider boundaries.

Reasoning:

- `baostock` is sufficient for first-version A-share daily K-line data.
- `tushare` has a more structured ecosystem but introduces token, points, permission, and rate-limit concerns.
- `akshare` has broad coverage but can require more defensive adaptation because upstream data shapes can vary by endpoint.
- First-version risk is not a lack of data sources; it is inconsistent field semantics, mixed adjustment modes, and weak cache validation.

## Critical Data Design Decision

The most important design correction was:

```text
qfq data is for signals.
raw data is for execution.
```

Reasoning:

- Forward-adjusted prices are useful for continuous historical features, indicators, and sweeps.
- Forward-adjusted prices are not actual historical tradable prices.
- Using qfq OHLC directly for execution would make historical fills unrealistic.
- Paper trading and live migration will be easier if the data model already separates signal and execution prices.

Implemented behavior:

- Cache can store `adjust=qfq`, `adjust=raw`, and `adjust=hfq` separately.
- Backtrader validation defaults to `signal_adjust=qfq` and `execution_adjust=raw`.
- Backtrader feeds expose raw OHLC as standard lines and qfq OHLC as `signal_*` lines.

## Implemented V1 Data Layer

Implemented modules:

- `MarketDataProvider` protocol.
- `BaostockProvider.get_daily_bars()`.
- `AkshareProvider` and `TushareProvider` stubs with `NotImplementedError`.
- `to_internal_symbol()` and `to_vendor_symbol()`.
- `ParquetCache`.
- Data quality validation.
- vectorbt adapter.
- backtrader data adapter.

Standard symbol format:

```text
Internal: 000001.SZ, 600000.SH
Baostock: sz.000001, sh.600000
```

The v1 implementation rejects unsupported aliases like `000001.XSHE` and `600000.XSHG` rather than silently normalizing them.

Baostock adjustment mapping:

```python
INTERNAL_ADJUST_TO_BAOSTOCK = {
    "hfq": "1",
    "qfq": "2",
    "raw": "3",
}
```

Cache structure:

```text
data/cache/a_share/daily/
  source=baostock/
    adjust=qfq/
      symbol=000001.SZ/part.parquet
    adjust=raw/
      symbol=000001.SZ/part.parquet
```

The cache stores metadata in both the path and Parquet file metadata:

- `source`
- `market`
- `frequency`
- `adjust`
- `calendar`

## Implemented Backtrader Module

The second implementation stage completed the first usable backtrader validation module.

Implemented modules:

- `backtrader_engine.py`
- `feeds.py`
- `analyzers.py`
- `models.py`
- `strategies.py`

Core behavior:

- `BacktraderConfig` defines symbols, date range, cash, cost assumptions, source, signal adjustment, execution adjustment, and execution timing.
- `BacktraderEngine` loads cached qfq signal data and raw execution data.
- `ASharePandasData` exposes raw execution OHLC as normal backtrader lines and qfq fields as `signal_open`, `signal_high`, `signal_low`, `signal_close`, `signal_volume`.
- `SignalSmaCrossStrategy` is a built-in example strategy that computes SMA crossovers on `signal_close`.
- Analyzers produce normalized equity curve, order log, trade log, and metrics.

Default execution assumptions:

- `signal_adjust=qfq`
- `execution_adjust=raw`
- `execution_timing=next_open`
- `commission_bps=3.0`
- `slippage_bps=5.0`

`same_close` is supported for strategies that can legitimately produce signals before the close, but `next_open` is the safer default.

## CLI State

Current CLI commands:

```bash
uv run quant-data download --symbols 000001.SZ --start 20200101 --end 20251231 --adjust qfq
uv run quant-data download --symbols 000001.SZ --start 20200101 --end 20251231 --adjust raw
uv run quant-data update --symbols 000001.SZ --start 20200101 --end 20251231 --adjust qfq
uv run quant-data inspect --symbols 000001.SZ --adjust qfq
```

Backtrader validation:

```bash
uv run quant-backtest validate \
  --symbols 000001.SZ \
  --signal-adjust qfq \
  --execution-adjust raw \
  --execution-timing next_open \
  --fast-period 5 \
  --slow-period 20
```

## Verification

Environment:

- Managed by `uv`.
- `.venv` uses Python `3.12.13`.
- The environment was recreated with the Codex bundled Python runtime because the first conda Python `3.11.5` environment caused pytest to segfault before running tests.

Verified command:

```bash
uv run pytest
```

Latest result after backtrader module implementation:

```text
19 passed
```

## Current Limitations

- No real A-share data has been downloaded yet.
- The current strategy is only a built-in SMA cross example.
- `vectorbt` sweep is still only a data loading scaffold, not a full strategy sweep framework.
- `akshare` and `tushare` providers are intentionally not implemented.
- Backtrader result export exists as frames in memory, but no CLI `--out` export is implemented yet.
- No DuckDB query layer is implemented.
- No paper trading layer is implemented.

## Next Likely Development Directions

- Implement a formal strategy interface for backtrader validation.
- Add result export to CSV/Parquet.
- Implement a `vectorbt` sweep module that can pass top candidates into backtrader validation.
- Add a DuckDB reader over Parquet cache for cross-sectional queries.
- Add real baostock download smoke tests behind an optional integration-test marker.
- Add richer A-share constraints: ST filtering, suspension handling, limit-up/limit-down constraints, lot-size rules, and trade calendar checks.
