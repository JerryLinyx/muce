# 2026-05-07 Three-Rising Factor MVP

## Context

The first concrete backtrader MVP strategy is a single-stock A-share factor test on 兆易创新.

Target stock:

```text
603986.SH
```

Factor idea:

```text
If a stock has three consecutive bullish daily candles, buy at the close of the third bullish day, hold for one trading day, and sell at the next close.
```

This is an MVP strategy for validating the backtrader module and qfq-signal/raw-execution data design. It is not yet a robust trading conclusion.

## Rule Definition

Entry condition:

- Use qfq signal data.
- For current day `t`, require:
  - `signal_close[t] > signal_open[t]`
  - `signal_close[t-1] > signal_open[t-1]`
  - `signal_close[t-2] > signal_open[t-2]`

Entry execution:

- Submit target-percent buy order on day `t`.
- Use `execution_timing=same_close`.
- Fill at raw close on day `t`.

Exit condition:

- Hold for `hold_bars=1`.

Exit execution:

- Submit target-percent zero order on day `t+1`.
- Fill at raw close on day `t+1`.

Default sizing:

```text
target_percent = 0.95
```

Default costs:

```text
commission_bps = 3
slippage_bps = 5
```

## Bias And Assumptions

This strategy intentionally uses same-close execution because the requested rule is "third-day close buy, next-day sell."

This creates an important assumption:

```text
The signal must be observable before the close and executable at that close.
```

In real trading, this is optimistic unless the strategy can identify the third bullish day near the close and execute reliably before the auction/close. For robustness testing, a later variant should compare:

- same close entry and same close exit
- next open entry and next open exit
- worse slippage assumptions
- delayed entry by one bar

## Implementation

Added:

- `get_three_rising_hold_one_day_strategy_class()`
- CLI strategy selector:
  - `--strategy sma-cross`
  - `--strategy three-rising-hold-one`
- CLI parameters:
  - `--target-percent`
  - `--hold-bars`

Backtrader feed semantics are unchanged:

- raw OHLCV lines drive execution and broker value.
- qfq `signal_*` lines drive factor calculation.

## Verification

Added unit test:

```text
test_three_rising_strategy_buys_third_close_and_sells_next_close
```

The test creates artificial `603986.SH` qfq/raw bars and verifies:

- three qfq bullish candles trigger entry
- buy fills on the third day raw close
- sell fills on the next day raw close
- one closed trade is recorded

## Next Steps

- Download `603986.SH` qfq and raw daily bars for the past year.
- Run `quant-backtest validate` with:
  - `--strategy three-rising-hold-one`
  - `--execution-timing same_close`
- Export metrics, order log, and trade log to files.
- Add a `next_open` comparison run to estimate same-close optimism.

## First Real-Data Run

Date range:

```text
2025-05-07 to 2026-05-07
```

Downloaded data:

```text
603986.SH qfq: 243 rows
603986.SH raw: 243 rows
```

Cache inspection:

- Missing OHLC: 0
- Duplicate rows: 0
- Suspended rows: 0
- ST rows: 0
- Warning: date gaps detected. This is expected with the current simple date-gap heuristic because it does not yet use an exchange trading calendar.

Backtest command:

```bash
uv run quant-backtest validate \
  --symbols 603986.SH \
  --start 20250507 \
  --end 20260507 \
  --strategy three-rising-hold-one \
  --signal-adjust qfq \
  --execution-adjust raw \
  --execution-timing same_close \
  --target-percent 0.95 \
  --hold-bars 1 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5
```

Result:

```text
start_cash: 1,000,000.00
final_value: 947,948.03
total_return: -5.2052%
annual_return: -5.3927%
max_drawdown_pct: 10.8945%
sharpe: -0.0307
completed_orders: 40
closed_trades: 20
win_rate: 40.0%
avg_pnl_comm: -2,602.60
best_pnl_comm: 56,892.93
worst_pnl_comm: -49,410.85
```

Initial interpretation:

- The MVP factor runs end to end and generates a reasonable number of trades for a one-year single-stock smoke test.
- The first run is negative after costs and should not be treated as a tradable edge.
- The sample is too small for confidence: one stock, one year, 20 closed trades.
- The same-close assumption is optimistic; a next-open variant is needed before drawing any conclusion.
