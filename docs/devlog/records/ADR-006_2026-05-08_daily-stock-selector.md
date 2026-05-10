---
id: ADR-006
kind: decision
title: Daily Stock Selector
date: 2026-05-08
status: accepted
---

# ADR 0006: Daily Stock Selector

## Status

Accepted

## Context

The system needs more than single-symbol strategy validation. We need a daily selector that scans a stock universe and emits candidates based on multiple technical factors, such as moving-average breakouts, KDJ golden crosses, MACD golden crosses, RSI momentum, volume breakouts, and Bollinger-band breakouts.

The selector should be separate from the execution backends. It should produce an auditable candidate table first, and the backtesting layer should convert candidates into orders or signals.

## Decision

Add a `quant_backtest.selection` layer.

First version components:

```text
FactorSelectorConfig
build_factor_table()
select_candidates()
run_selection_backtest()
run_selection_hit_rate()
quant-select candidates
quant-select backtest
quant-select hit-rate
quant-select sweep-hit-rate
```

The selector computes factor booleans and a simple additive `factor_score`. Candidates are selected when:

```text
tradable == True
factor_score >= min_score
```

Candidates are ranked by:

```text
date, factor_score desc, amount desc, volume desc, symbol asc
```

The first selector backtest is a VectorBT research backtest:

```text
signals computed on qfq bars
execution close taken from raw bars
selected candidates enter at target_percent_per_position
exit after hold_days
cash_sharing=True for portfolio-level cash
```

## Factor Semantics

Current MVP factors:

```text
ma_breakout:
  close crosses above MA(short), with MA(short) > MA(long)

kdj_golden_cross:
  K crosses above D

macd_golden_cross:
  MACD diff crosses above DEA/signal

rsi_momentum:
  RSI >= configured threshold

volume_breakout:
  volume >= volume MA * configured multiplier

boll_breakout:
  close crosses above upper Bollinger band
```

## Rationale

- The selector table is inspectable before any backtest is run.
- The selector can later be reused by Backtrader, VectorBT, or a live/paper trading layer.
- qfq signal and raw execution semantics remain consistent with the existing backtest system.
- The first scoring model is deliberately simple so later factor weighting and IC analysis can be added without hiding assumptions.

## Implementation

- Factor table computation via `build_factor_table()` with per-symbol technical indicators
- Candidate ranking by `factor_score desc, amount desc, volume desc, symbol asc`
- Tradability filters: suspended and ST exclusion by default
- `entry_lag_days=1` default to avoid same-day-close look-ahead bias
- CLI: `quant-select candidates`, `quant-select backtest`
- Full-market smoke test: 9414 candidates, -0.52% return with simple equal-weight scoring
- Key finding: `min_score=4` produces ~68 candidates/day before Top-N truncation
- `tests/test_selection.py`: 19 tests passed
- TA-Lib oracle: `src/quant_backtest/features/talib_oracle.py` for optional cross-checking

## Consequences

- Current selector is a research MVP, not a production portfolio allocator.
- It does not yet handle industry neutrality, liquidity filters beyond amount/volume ranking, max positions, turnover constraints, T+1, limit-up/limit-down, or rebalance calendars.
- Full-market usage requires downloading the full A-share universe qfq/raw daily cache first.
- Hit-rate validation is now separate from portfolio backtesting. It should be used first to check factor directionality before spending time on Backtrader execution details.
