# Muce 牧策 — Current State

A-share multi-factor quantitative research and backtesting toolkit.

## Status

Research MVP. Core data + backtest infrastructure is functional. Engineering layer (unified model, market rules, risk control) is under construction in P0 phase.

## Current Version

v0.1.0 — active development, not yet versioned for release.

## What Works

- Baostock daily data download (qfq + raw), Parquet cache for ~5200 symbols, 1 year
- Technical indicators: MA, EMA, MACD, KDJ, RSI, Bollinger Bands, ATR, OBV
- Full-market daily multi-factor stock selector with hard require/exclude filters
- VectorBT fast parameter sweeps (3 strategies)
- Backtrader event-driven validation with qfq-signal / raw-execution semantics
- Selector execution simulation with A-share constraints (lot size, limit-up/down)
- Selector Backtrader validation
- Simulator vs Backtrader divergence diagnostics (gap reduced from 36% to 28%)
- FastAPI read-only API (data, selection, reports)
- Report artifact format: manifest.json + parquet under reports/sweeps/ and reports/validations/
- Test suite: 101 passed, 4 skipped

## Current P0 Priorities

1. P0-4: Unified Portfolio / Broker / Order / Fill model — **active**
2. P0-5: A-share market rules engine
3. P0-2: Realistic next-open sizing in simulator
4. P0-3: Strategy-level skipped-candidate logging
5. P0-6: Feature and factor cache