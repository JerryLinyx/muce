# 2026-05-09 Validation Gap Diagnostics

## Context

The project had a material gap between the fast selector execution simulator and Backtrader validation for the same strict selector candidate.

Current candidate:

```text
require: kdj_golden_cross, macd_golden_cross, rsi_momentum, boll_breakout
exclude: ma_breakout, volume_breakout
rsi_threshold: 70
boll_std: 1.5
top_n: 3
execution_timing: next_open
hold_days: 10
target_percent_per_position: 20%
max_positions: 2
take_profit_pct: none
stop_loss_pct: none
```

Before this work, the simulator reported a much stronger result than Backtrader. This blocked trustworthy strategy research.

## Decision

Implemented a dedicated validation-gap diagnostic workflow instead of immediately changing either engine.

New module:

```text
src/quant_backtest/selection/diagnostics.py
```

New CLI:

```bash
quant-select diagnose-validation-gap
```

The diagnostic runs both engines for the same selector and execution config, normalizes orders and equity curves, and reports:

- metric differences
- first order divergence
- first equity divergence
- order divergence categories
- equity divergence categories
- exportable artifacts

## Implementation

Added:

```text
SelectorValidationGapConfig
run_selector_validation_gap()
normalize_simulator_orders()
normalize_backtrader_orders()
normalize_simulator_equity()
normalize_backtrader_equity()
compare_order_summaries()
compare_equity_curves()
```

The CLI supports:

```bash
quant-select diagnose-validation-gap \
  --start 20250507 \
  --end 20260507 \
  --min-score 4 \
  --require-factors kdj_golden_cross,macd_golden_cross,rsi_momentum,boll_breakout \
  --exclude-factors ma_breakout,volume_breakout \
  --rsi-threshold 70 \
  --boll-std 1.5 \
  --top-n 3 \
  --execution-timing next_open \
  --hold-days 10 \
  --target-percent-per-position 20 \
  --max-positions 2 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5 \
  --out reports/validation-gap/selector-rsi70-boll15-next-open
```

Artifacts written:

```text
reports/validation-gap/selector-rsi70-boll15-next-open/
  summary.json
  simulator_orders.csv
  backtrader_orders.csv
  order_comparison.csv
  simulator_equity.csv
  backtrader_equity.csv
  equity_comparison.csv
  candidates.csv
```

## Findings

Summary:

```text
simulator_total_return: 66.89%
backtrader_total_return: 30.45%
total_return_diff: 36.43 percentage points

simulator_sharpe: 2.71
backtrader_sharpe: 1.89
sharpe_diff: 0.82

simulator_max_drawdown: 7.33%
backtrader_max_drawdown: 9.03%

simulator_filled_orders: 65
backtrader_filled_orders: 51
simulator_rejected_orders: 103
backtrader_rejected_orders: 0
```

First order divergence:

```text
date: 2025-06-27
symbol: 300502.SZ
side: buy
category: sizing
simulator_shares: 1700
backtrader_shares: 1712
simulator_price: 115.8579
backtrader_price: 115.8579
```

Same date also shows symbol-selection divergence:

```text
simulator bought: 300635.SZ
Backtrader bought: 601577.SH
category: missing_in_backtrader / missing_in_simulator
```

First equity divergence:

```text
date: 2025-06-27
simulator_value: 1009207.82
backtrader_value: 1005746.09
value_diff: 3461.73
cash_diff: 1839.12
category: value_and_cash
```

Divergence categories:

```text
missing_in_backtrader: 47
missing_in_simulator: 33
sizing: 9
sizing_and_fill_price: 9
equity_value_and_cash: 207
```

## Interpretation

The gap is not caused by final metric calculation. The first divergence happens on the first fill date.

Likely causes to address next:

1. Candidate priority is not preserved in Backtrader validation.
   - The simulator processes the selected candidate table order.
   - Backtrader receives only `signals_by_symbol` and then re-ranks signaled symbols inside the strategy.
   - This can choose a different symbol when `top_n > max_positions`.

2. Backtrader sizing does not enforce A-share lot-size rounding.
   - The simulator rounds to 100-share lots.
   - Backtrader `order_target_percent` produced odd-lot sizes such as `1712`.

3. Exit timing and fill semantics differ.
   - Some sell rows show `sizing_and_fill_price`, not only share-count differences.
   - The Backtrader strategy records `entry_bar` when submitting a buy order, not necessarily when the order is completed.
   - This can affect hold-period semantics under `next_open`.

4. Rejection accounting differs.
   - The simulator records skipped candidates as rejected buy rows.
   - Backtrader does not currently record strategy-level skipped candidates as rejected orders.

## Verification

```bash
uv run pytest tests/test_selection.py
```

Result:

```text
19 passed
```

## Next Steps

The next implementation step should be to reduce semantic differences before adding new strategy searches:

1. Preserve per-date candidate rank/order in Backtrader validation.
2. Add A-share lot-size sizing to Backtrader selector validation.
3. Set Backtrader `entry_bar` on completed buy order, not on order submission.
4. Add strategy-level rejection/skipped-candidate logs or keep them explicitly separate from broker rejections.
5. Re-run `diagnose-validation-gap` and require the first divergence to move later or become explainable.

## Validation Semantics Update

Implemented the first three fixes:

- Backtrader validation now passes a per-date ordered candidate list into the selector strategy, preserving selector ranking.
- The selector strategy uses explicit share orders rounded by `lot_size` instead of `order_target_percent`, avoiding odd-lot sizes.
- Buy `entry_bar` is recorded on completed fill and adjusted to the filled bar index.
- For `next_open`, Backtrader no longer blocks entries because the signal-day close is limit-up. This avoids incorrectly rejecting stocks that open tradably the next day.
- Exits use an explicit close order so the validation path is closer to the simulator's close-price exit semantics.

Rejected approach:

- I tested Backtrader `cheat_on_open` for next-open entries, but in this feed setup it produced signal-day open fills for this workflow. That is earlier than the intended next-open execution and would introduce look-ahead-like behavior, so it was not kept.

Latest diagnostic artifact:

```text
reports/validation-gap/selector-rsi70-boll15-next-open-v6/
```

Latest summary:

```text
simulator_total_return: 66.89%
backtrader_total_return: 38.84%
total_return_diff: 28.04 percentage points

simulator_sharpe: 2.71
backtrader_sharpe: 1.51

simulator_max_drawdown: 7.33%
backtrader_max_drawdown: 15.09%

simulator_filled_orders: 65
backtrader_filled_orders: 61
```

First remaining order divergence:

```text
date: 2025-06-27
symbol: 300635.SZ
side: buy
category: sizing
simulator_shares: 15900
backtrader_shares: 15000
simulator_price: 12.556275
backtrader_price: 12.556275
```

Interpretation:

- The first divergence is now sizing, not symbol selection or odd-lot behavior.
- This remaining difference is expected: the simulator sizes using the known next-open fill price, while Backtrader sizes from information available at signal-day close and then fills at next open.
- The simulator is therefore still optimistic for next-open sizing. Backtrader is the more conservative validation reference.
- Further convergence should be done by adding a simulator option for realistic next-open sizing, not by making Backtrader use future open prices.

Verification:

```bash
uv run pytest
```

Result:

```text
60 passed, 3 skipped
```
