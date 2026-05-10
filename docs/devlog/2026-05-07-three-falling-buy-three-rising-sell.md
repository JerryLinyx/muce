# 2026-05-07 Three-Falling Buy And Three-Rising Sell

## Context

The second concrete Backtrader MVP strategy tests a simple reversal-and-exit rule on 兆易创新.

Target stock:

```text
603986.SH
```

Date range:

```text
2025-05-07 to 2026-05-07
```

Strategy idea:

```text
If the stock has three consecutive bearish daily candles, buy and hold.
If the stock later has three consecutive bullish daily candles, sell.
```

## Rule Definition

Entry condition:

- Use qfq signal data.
- When flat, buy if the current day and previous two days all satisfy:

```text
signal_close < signal_open
```

Exit condition:

- Use qfq signal data.
- When holding, sell if the current day and previous two days all satisfy:

```text
signal_close > signal_open
```

Execution:

- Use raw execution data.
- Use `execution_timing=same_close`.
- Buy and sell at the signal day's raw close.

Default sizing and costs:

```text
target_percent = 0.95
commission_bps = 3
slippage_bps = 5
```

## Implementation

Added:

- `get_three_falling_buy_three_rising_sell_strategy_class()`
- CLI option:
  - `--strategy three-falling-buy-three-rising-sell`
- CLI parameter:
  - `--signal-count 3`

Also refactored shared candle helpers:

- `_is_n_rising()`
- `_is_n_falling()`
- `_has_pending_order()`

## Verification

Added unit test:

```text
test_three_falling_buy_three_rising_sell_strategy
```

The test verifies:

- three qfq bearish candles trigger a buy
- three qfq bullish candles trigger a sell
- executions happen on raw close under `same_close`
- a closed trade is recorded

Full test suite:

```text
21 passed
```

## Real-Data Run

Command:

```bash
uv run quant-backtest validate \
  --symbols 603986.SH \
  --start 20250507 \
  --end 20260507 \
  --strategy three-falling-buy-three-rising-sell \
  --signal-adjust qfq \
  --execution-adjust raw \
  --execution-timing same_close \
  --target-percent 0.95 \
  --signal-count 3 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5
```

Result:

```text
start_cash: 1,000,000.00
final_value: 1,422,085.42
total_return: 42.2085%
annual_return: 44.0753%
max_drawdown_pct: 21.0836%
sharpe: 0.0765
completed_orders: 22
closed_trades: 11
win_rate: 72.7273%
avg_pnl_comm: 38,371.40
best_pnl_comm: 241,363.59
worst_pnl_comm: -111,815.68
```

Initial interpretation:

- The strategy is strongly positive in this one-stock, one-year sample.
- The result relies on only 11 closed trades, so confidence is low.
- The same-close execution assumption is optimistic.
- The maximum drawdown is high relative to trade count.
- The large best trade contributes heavily to total performance.

## Next Questions

- Does the result survive `next_open` execution?
- Does it survive higher slippage assumptions?
- Does it work over 3-5 years?
- Does it work on a broader semiconductor or A-share universe?
- Is the result mostly driven by one strong trend period in 2025?
