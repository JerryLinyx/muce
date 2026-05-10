---
id: ADR-008
kind: decision
title: Selector Hit-Rate Validation And Diagnostics
date: 2026-05-09
status: accepted
---

# ADR 0008: Selector Hit-Rate Validation

## Status

Accepted

## Implementation

- Hit-rate module: `hit_rate.py`, `attribution.py` — separate factor directionality from portfolio construction
- Strict filters: `require_factors` / `exclude_factors` for hard factor inclusion/exclusion
- Execution-aware simulation: `execution.py` with lot size, limit-up/down, surge slippage, position limits
- Sweep-simulate: layered parameter grids (hold days, target percent, max positions, top-N) with factor threshold layers (rsi_threshold, boll_std, volume_multiplier)
- Backtrader selector validation: `backtrader_validation.py` with precomputed signal dates, close-confirmed take-profit
- Layered sweeps: factor parameters swept alongside execution parameters in one pipeline
- CLI: `quant-select hit-rate`, `quant-select attribution`, `quant-select simulate`, `quant-select sweep-simulate`, `quant-select validate-backtrader`

## Context

The selector backtest answers a portfolio question: if selected names are traded with cash, sizing, fees, slippage, and holding rules, what happens to equity?

Before treating the selector as a tradable strategy, we also need a cleaner factor question:

```text
If we select N stocks near today's close, how often are those names up by the next close?
```

This separates factor directionality from portfolio construction.

## Decision

Add a selector hit-rate module:

```text
SelectionHitRateConfig
run_selection_hit_rate()
evaluate_candidate_hit_rate()
summarize_daily_hit_rate()
summarize_factor_attribution()
sweep_selection_hit_rate()
quant-select hit-rate
quant-select attribution
quant-select sweep-hit-rate
```

Default evaluation:

```text
signal data: qfq
execution/evaluation data: raw
price mode: close_to_next_close
forward_days: 1
```

Daily output includes:

```text
signal_count
valid_count
win_count
loss_count
flat_count
invalid_count
win_rate
avg_forward_return
median_forward_return
```

Overall output includes:

```text
total_signals
valid_signals
win_rate
avg_daily_win_rate
positive_day_rate
avg_forward_return
median_forward_return
```

`sweep-hit-rate` reads cached market data once and reuses computed factor tables when only `top_n` and `min_score` change.

## Rationale

- Win rate is easier to interpret than equity curves when tuning selector filters.
- Daily win rate shows regime dependence and prevents one good day from hiding weak day-to-day behavior.
- qfq signal and raw forward-return evaluation preserve the dual-price convention.
- Invalid rows are kept visible, usually because the final signal date has no next trading day in the cache.

## Current Baseline

Using the one-year full-market cache:

```text
range: 2025-05-07 to 2026-05-07
universe: 5200 symbols
min_score: 4
top_n: 10
forward_days: 1
price_mode: close_to_next_close
```

Result:

```text
signal_days: 223
total_signals: 2223
valid_signals: 2213
win_rate: 46.27%
avg_daily_win_rate: 46.25%
positive_day_rate: 56.50%
avg_forward_return: 0.37%
median_forward_return: -0.27%
```

The hit rate is below 50%, and the median next-day return is negative. The current equal-weighted technical-factor voting rule should be treated as a functional MVP, not as a validated alpha.

## Strict Filtering Update

The selector now supports hard filters:

```text
require_factors
exclude_factors
```

The first useful strict interaction was:

```text
require:
  kdj_golden_cross
  macd_golden_cross
  rsi_momentum
  boll_breakout

exclude:
  ma_breakout
  volume_breakout
```

Close-to-next-close, `top_n=1`, one-year full-market result:

```text
valid_signals: 135
win_rate: 64.44%
avg_forward_return: 2.41%
median_forward_return: 0.99%
```

Next-open-to-next-close, `top_n=1`, result:

```text
valid_signals: 135
win_rate: 50.37%
avg_forward_return: 0.81%
median_forward_return: 0.02%
```

This rule is promising as a research candidate, but its performance is sensitive to execution timing. It must go through Backtrader-style execution validation, liquidity checks, limit-up/limit-down checks, and walk-forward testing before being considered tradable.

## Execution-Aware Simulation Update

Added `quant-select simulate` to test selector rules with execution constraints before moving them into Backtrader.

Modeled constraints:

```text
entry lag
open/close entry and exit fields
fixed holding days
target percent allocation
max concurrent positions
100-share lot rounding
commission
base slippage
extra surge slippage
limit-up buy rejection
limit-down sell rejection
```

For the strict rule, using 20% per position and max one position:

```text
same-day close entry, hold 1 day:
  total_return: 6.47%
  max_drawdown: 4.94%
  limit_up_buy_rejections: 69

next-open entry, hold 1 day:
  total_return: 31.89%
  max_drawdown: 10.05%
  limit_up_buy_rejections: 10
  limit_down_sell_rejections: 5

next-open entry, hold 2 days:
  total_return: 31.03%
  max_drawdown: 7.60%
  limit_up_buy_rejections: 6
  limit_down_sell_rejections: 1
```

Decision impact:

- Limit-up buy rejection materially changes the result and must remain enabled for A-share selector validation.
- Holding period cannot be chosen independently from position count and target allocation because longer holds block later signals.
- The next validation step should sweep holding days, position count, and allocation together under these execution constraints.

## Sweep Update

Added `quant-select sweep-simulate` for execution-aware parameter sweeps.

Initial close-time sweep covered:

```text
hold_days: 1,2,3,4,5
target_percent_per_position: 5%,10%,20%,30%
max_positions: 1,2,3,5
top_n: 1,2,5
```

Best Sharpe region:

```text
hold_days: 5
max_positions: 1
top_n: 5
```

Adding stop-loss/take-profit around that region found:

```text
hold_days: 5
target_percent_per_position: 30%
max_positions: 1
top_n: 5
take_profit_pct: 20%
stop_loss_pct: none
total_return: 55.14%
max_drawdown: 7.95%
sharpe: 2.63
```

A lower-risk candidate is:

```text
hold_days: 5
target_percent_per_position: 20%
max_positions: 1
top_n: 5
take_profit_pct: 20%
stop_loss_pct: none
total_return: 34.10%
max_drawdown: 5.34%
sharpe: 2.63
```

Decision impact:

- Use the 20% allocation candidate as the next Backtrader validation target.
- Treat the 30% allocation candidate as an aggressive research reference, not the default.
- Do not add stop-loss just because it sounds safer; in the current daily-bar approximation, `-5%` stop-loss did not beat the best 20% take-profit rows.

## Backtrader Validation Update

Added `quant-select validate-backtrader` to validate precomputed selector signals through Backtrader.

Backtrader validation loads only candidate symbols instead of the full 5200-symbol universe. For the current strict selector:

```text
candidate_count: 300
validation_symbol_count: 281
```

Results:

```text
same_close, hold 5, 20% allocation, max 1 position, 20% close-confirmed take-profit:
  total_return: 20.37%
  max_drawdown: 4.85%
  sharpe: 1.94

same_close, hold 5, 20% allocation, max 1 position, no take-profit:
  total_return: 25.11%
  max_drawdown: 4.85%
  sharpe: 2.33

next_open, hold 5, 20% allocation, max 1 position, no take-profit:
  total_return: 19.18%
  max_drawdown: 5.51%
  sharpe: 1.78
```

Decision impact:

- The daily-high take-profit used in the simulator is too optimistic for validation.
- The current Backtrader validation target is now the no-take-profit version:

```text
top_n: 5
hold_days: 5
target_percent_per_position: 20%
max_positions: 1
take_profit_pct: none
stop_loss_pct: none
```

This is the cleaner candidate to carry into minute-data validation.

## Consequences

- The next selector work should optimize for robustness, not just average return.
- We need factor-level contribution analysis and walk-forward validation before using these rules for trading decisions.
- The current Pandas implementation is acceptable for one-year experiments but should eventually cache feature tables or use DuckDB/Polars for faster repeated sweeps.

## Layered Sweep Update

`quant-select sweep-simulate` now supports factor-parameter layers:

```text
--min-score-list
--rsi-threshold-list
--volume-multiplier-list
--boll-std-list
```

Decision impact:

- Keep the sweep pipeline layered: first broad execution grid, then factor threshold grid, then Backtrader validation.
- Do not select a candidate only because it is the highest simulator row.
- Treat Backtrader as the conservative validation backend when simulator and Backtrader differ materially.

Latest one-year strict selector candidate:

```text
require: kdj_golden_cross, macd_golden_cross, rsi_momentum, boll_breakout
exclude: ma_breakout, volume_breakout
rsi_threshold: 70
boll_std: 1.5
top_n: 3
hold_days: 10
target_percent_per_position: 20%
max_positions: 2
take_profit_pct: none
stop_loss_pct: none
```

Simulator next-open result:

```text
total_return: 66.60%
max_drawdown: 7.37%
sharpe: 2.70
candidate_count: 138
```

Backtrader validation result:

```text
next_open:
  total_return: 30.45%
  max_drawdown: 9.03%
  sharpe: 1.89

same_close:
  total_return: 30.48%
  max_drawdown: 9.32%
  sharpe: 1.88
```

The size of this gap means the simulator remains a fast search tool, not the final validation authority. The next engineering task is to diagnose simulator-vs-Backtrader differences in order timing, sizing, and mark-to-market semantics before expanding the search space further.
