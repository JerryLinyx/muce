---
id: ADR-010
kind: review
title: Three-Falling Buy / Three-Rising Sell Strategy Validation
date: 2026-05-07
status: accepted
---

# ADR-010: Three-Falling Buy / Three-Rising Sell Strategy Validation

## Context

The second concrete Backtrader MVP strategy tested a reversal-and-exit rule on 603986.SH (兆易创新) over 2025-05-07 to 2026-05-07.

Rule: three consecutive bearish daily candles → buy; three consecutive bullish daily candles → sell. Execution: same-close on raw prices, 95% target allocation, 3bps commission, 5bps slippage.

## Decision

Implement the strategy as a Backtrader strategy class and VectorBT signal builder. Run both engines for cross-validation.

## Implementation

- `get_three_falling_buy_three_rising_sell_strategy_class()` — Backtrader strategy
- CLI: `--strategy three-falling-buy-three-rising-sell`, `--signal-count N`
- Shared candle helpers: `_is_n_rising()`, `_is_n_falling()`
- `quant-backtest validate` real-data run on 603986.SH

Backtrader result (same_close):
- final_value: 1,422,085.42 (42.21% return)
- max_drawdown: 21.08%
- 11 closed trades, 72.73% win rate
- best trade: +241,363.59, worst: -111,815.68

VectorBT sweep over signal_count=2,3,4:
- signal_count=4: 89.20% return, 4 trades
- signal_count=3: 42.10% return, 11 trades
- signal_count=2: 6.93% return, 19 trades

## Cross-Engine Validation

No costs: Backtrader and VectorBT match to floating-point precision (1,444,922.53 final value).

With costs (3bps commission, 5bps slippage): Backtrader 1,422,085.42 vs VectorBT 1,420,905.56 (diff 1,179.86). Acceptable for research screening.

## Risk-Control Sweeps

4900-parameter sweep on 603986.SH:
- Best total return: 50% exposure, 7 max hold days, 5% stop-loss, 20% take-profit → 22.46%
- Best Sharpe: 50% exposure, 1 max hold day, 5% take-profit → Sharpe 1.63

Pyramiding sweep (from_orders, max_position_percent):
- Best pyramiding: 34.65% return (vs non-pyramiding 22.46%)
- Max drawdown increased from 7.28% to 8.88%

## Consequences

- The strategy is strongly positive in one-stock/one-year sample but relies on only 11 trades
- The result is likely driven by one large trend trade on 603986.SH
- same_close execution is optimistic; next_open variant needed for robustness
- Single-stock, single-year sample is too small for confidence
- Pyramiding increased return at the cost of full capital usage near max exposure
