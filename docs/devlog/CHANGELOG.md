# Changelog

All notable changes to this project will be recorded here. Follows devlog topology — detailed decisions in `records/`, current state in `current/`.

## Unreleased (v0.1.0-dev)

### 2026-05-10 — FastAPI Read-Only Backend
- Added services/ layer wrapping existing modules
- FastAPI app with system, data, selection, reports routers
- Job-based selection with SSE progress streaming
- Report artifact format: manifest.json + parquet under reports/sweeps/ and reports/validations/
- CLI sweep/validate write reports by default
- 23 new tests, total 101 passed (+42 from previous baseline)

### 2026-05-09 — Validation Gap Diagnostics
- Implemented simulator vs Backtrader comparison tool
- Six revisions reduced gap from 36% to 28% total return difference
- Fixes: selector candidate order preserved, lot-size sizing, entry_bar on fill, exit close orders
- Remaining gap is sizing (simulator uses future open price → P0-2)

### 2026-05-08 — Daily Stock Selector
- Full-market multi-factor selector with 6 technical factors
- Hit-rate analysis and factor attribution
- Strict filter support (require_factors, exclude_factors)
- Execution simulation with A-share constraints
- Parameter sweeps with layered factor grids
- Backtrader selector validation
- One-year full-market data: 5200 symbols, 2.5M rows

### 2026-05-08 — Technical Indicator Layer
- Pure-Python indicators: SMA, EMA, MACD, RSI, KDJ, Bollinger, ATR, OBV
- TA-Lib as optional oracle
- Cross-validated against VectorBT

### 2026-05-08 — Full-Market Storage
- Full-market batch download (--all-symbols, --adjust both)
- DuckDB optional query layer over Parquet

### 2026-05-07 — Project Origin
- Initial project setup: uv, Python 3.12, pytest
- Baostock data provider with Parquet cache
- Dual-engine design: VectorBT for sweeps, Backtrader for validation
- qfq-signal / raw-execution data semantics
- Backtrader validation engine with custom feed and SMA cross strategy
- Three-rising-hold-one MVP on 603986.SH
- Three-falling-buy-three-rising-sell strategy with cross-engine validation
- VectorBT sweep engine with parameter grids, pyramiding, risk-control sweeps