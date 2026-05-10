# 2026-05-07 VectorBT Research Engine

## Context

After completing the Backtrader validation module, the next step was to complete the VectorBT module for fast parameter sweeps.

The intended division remains:

```text
VectorBT -> fast research and parameter screening
Backtrader -> deeper validation and order-level logs
```

## Implementation

Added:

- `vectorbt_models.py`
- `vectorbt_strategies.py`
- `vectorbt_engine.py`

Updated:

- `VectorbtRunner`
- `quant-backtest sweep`
- root `README.md`
- docs index and backlog

Supported strategies:

- `sma-cross`
- `three-rising-hold-one`
- `three-falling-buy-three-rising-sell`

Data semantics:

- qfq panels are used for signal generation.
- raw close panels are used for vectorized execution.

Sizing:

- VectorBT uses `size_type="percent"` and `target_percent` as the entry percent of available cash.
- This is close to but not identical to Backtrader `order_target_percent`; Backtrader remains the validation source for execution-level comparison.

## CLI

Example:

```bash
uv run quant-backtest sweep \
  --symbols 603986.SH \
  --start 20250507 \
  --end 20260507 \
  --strategy three-falling-buy-three-rising-sell \
  --signal-adjust qfq \
  --execution-adjust raw \
  --signal-counts 2,3,4 \
  --target-percent 0.95 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5 \
  --rank-by total_return
```

## Real-Data Smoke Run

Using cached `603986.SH` qfq/raw data from `2025-05-07` to `2026-05-07`, the sweep over `signal_count=2,3,4` produced:

```text
signal_count=4: total_return 89.20%, trade_count 4, win_rate 25.00%, max_drawdown 20.26%
signal_count=3: total_return 42.10%, trade_count 11, win_rate 72.73%, max_drawdown 21.07%
signal_count=2: total_return  6.93%, trade_count 19, win_rate 52.63%, max_drawdown 21.76%
```

Interpretation:

- The VectorBT module is now able to rank parameter variants quickly.
- The `signal_count=4` result has the highest return but only 4 trades, so it is not necessarily more robust.
- `signal_count=3` is close to the Backtrader result but not identical because the two engines do not model sizing and order execution in exactly the same way.

## Verification

Full test suite:

```text
28 passed
```

Observed warnings:

- VectorBT under pandas 3 emits pandas deprecation warnings related to bool inversion in internal operations.
- The warnings did not fail tests, but should be watched if pandas/vectorbt versions change.

## Cross-Engine Validation

Added tests to compare Backtrader and VectorBT on the same cached data, signal logic, raw execution prices, and normalized equity-curve metrics.

Important implementation detail:

- Backtrader defaults to integer share fills.
- VectorBT defaults to fractional shares.
- VectorBT now uses `size_granularity=1.0` by default to align with Backtrader's integer-share behavior.

Metric normalization:

- `final_value`
- `total_return`
- `annual_return`
- `max_drawdown`
- `sharpe`

These are now calculated from each engine's equity curve using the shared `compute_equity_metrics()` helper instead of relying on each framework's native metric/analyzer definitions.

Real-data comparison on `603986.SH`, `2025-05-07` to `2026-05-07`, strategy `three-falling-buy-three-rising-sell`:

No commission/slippage:

```text
final_value:  Backtrader 1,444,922.53 | VectorBT 1,444,922.53
total_return: Backtrader 44.492253%   | VectorBT 44.492253%
max_drawdown: Backtrader 21.069135%   | VectorBT 21.069135%
sharpe:       Backtrader 1.292452     | VectorBT 1.292452
trade_count:  11                      | 11
```

With `commission_bps=3` and `slippage_bps=5`:

```text
final_value:  Backtrader 1,422,085.42 | VectorBT 1,420,905.56 | diff 1,179.86
total_return: Backtrader 42.208542%   | VectorBT 42.090556%   | diff 0.117986 pct points
max_drawdown: Backtrader 21.083610%   | VectorBT 21.066893%   | diff 0.016717 pct points
sharpe:       Backtrader 1.244029     | VectorBT 1.243324     | diff 0.000705
trade_count:  11                      | 11
```

Interpretation:

- Without costs, the engines match to floating-point precision.
- With costs, the remaining small difference comes from framework-specific order sizing, fee application, and slippage application details.
- This is acceptable for research screening, but Backtrader remains the validation source for final order-level analysis.

## Risk-Control Parameter Sweep

For the `three-falling-buy-three-rising-sell` strategy on `603986.SH`, ran a VectorBT sweep over:

```text
target_percent: 5%, 10%, ..., 50%
max_hold_days: 1, 2, ..., 10
stop_loss: None, -5%, -10%, -15%, -20%, -25%, -30%
take_profit: None, 5%, 10%, 15%, 20%, 25%, 30%
```

This is:

```text
10 * 10 * 7 * 7 = 4900 parameter combinations
```

Command:

```bash
uv run quant-backtest sweep \
  --symbols 603986.SH \
  --start 20250507 \
  --end 20260507 \
  --strategy three-falling-buy-three-rising-sell \
  --signal-adjust qfq \
  --execution-adjust raw \
  --signal-counts 3 \
  --target-percents 5,10,15,20,25,30,35,40,45,50 \
  --max-hold-days-list 1,2,3,4,5,6,7,8,9,10 \
  --stop-losses none,-5,-10,-15,-20,-25,-30 \
  --take-profits none,5,10,15,20,25,30 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5 \
  --rank-by total_return \
  --top 20
```

Top by total return:

```text
target_percent: 50%
max_hold_days: 7
stop_loss: -5%
take_profit: 20%
total_return: 22.46%
annual_return: 23.49%
max_drawdown: 7.28%
sharpe: 1.41
trade_count: 14
win_rate: 64.29%
```

Top by Sharpe and return/drawdown:

```text
target_percent: 50%
max_hold_days: 1
take_profit: 5%
stop_loss: mostly irrelevant across tested values
total_return: 12.77%
annual_return: 13.33%
max_drawdown: 3.84%
sharpe: 1.63
trade_count: 18
win_rate: 66.67%
```

Observations:

- The best total-return parameters are concentrated at the highest tested exposure, `target_percent=50%`.
- This is expected for a single-stock long-only strategy with mostly positive expectancy; higher exposure mechanically increases return and drawdown.
- `max_hold_days=7` dominates the top total-return group.
- `max_hold_days=1` dominates the best Sharpe and return/drawdown group.
- Stop-loss values did not form a clean monotonic pattern in the top groups; take-profit around `5%` helped risk-adjusted ranking, while `20%` appeared in the top total-return group.

Interpretation:

- If optimizing for raw return, the current sample favors `50%` exposure and `7` max holding days.
- If optimizing for risk-adjusted behavior, the current sample favors `50%` exposure, `1` max holding day, and `5%` take profit.
- Because this is still one stock and one year, these should be treated as candidate parameters, not selected parameters.
- The next validation step should run the top candidates in Backtrader and then test across more symbols and longer periods.

## Pyramiding Sweep

After reviewing the non-pyramiding strategy, we found that additional three-falling signals can occur while a position is already open. The original strategy ignored those signals, so the next research step added a pyramiding mode.

Implemented VectorBT pyramiding semantics:

```text
flat + three-falling signal => buy one target_percent tranche
holding + three-falling signal => add one target_percent tranche
total position target is capped by max_position_percent
holding + three-rising signal => exit to 0%
stop_loss / take_profit / max_hold_days can also exit to 0%
```

For pyramiding, `target_percent` means per-add tranche size, not final total position size. This is intentionally different from the original non-pyramiding mode, where `target_percent` meant the full target exposure. The first implementation uses VectorBT `from_orders` with explicit `targetpercent` orders instead of `from_signals(accumulate=True)`, because `accumulate=True` with percent sizing buys a percentage of remaining cash rather than targeting a clear portfolio exposure.

Sweep configuration on `603986.SH`, `2025-05-07` to `2026-05-07`:

```text
target_percent: 5%, 10%, ..., 50% per add
max_position_percent: 100%
max_hold_days: 1, 2, ..., 10
stop_loss: None, -5%, -10%, -15%, -20%, -25%, -30%
take_profit: None, 5%, 10%, 15%, 20%, 25%, 30%
```

Command:

```bash
uv run quant-backtest sweep \
  --symbols 603986.SH \
  --start 20250507 \
  --end 20260507 \
  --strategy three-falling-buy-three-rising-sell \
  --signal-adjust qfq \
  --execution-adjust raw \
  --signal-counts 3 \
  --target-percents 5,10,15,20,25,30,35,40,45,50 \
  --max-hold-days-list 1,2,3,4,5,6,7,8,9,10 \
  --stop-losses none,-5,-10,-15,-20,-25,-30 \
  --take-profits none,5,10,15,20,25,30 \
  --pyramiding \
  --max-position-percent 100 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5 \
  --rank-by total_return \
  --top 20
```

Top total-return group:

```text
target_percent: 50% per add
max_position_percent: 100%
max_hold_days: 9
stop_loss: mostly inactive among the top group
take_profit: mostly inactive above 20% among the top group
total_return: 34.65%
annual_return: 36.31%
max_drawdown: 8.88%
sharpe: 1.54
trade_count: 13
win_rate: 76.92%
entry_signal_count: 28
```

Comparison with the previous non-pyramiding sweep:

```text
best non-pyramiding total_return: 22.46%
best pyramiding total_return:     34.65%
best non-pyramiding max_drawdown: 7.28%
best pyramiding max_drawdown:     8.88%
```

Cash check:

```text
negative cash combinations: 0
lowest cash observed: 1.16
```

Interpretation:

- Pyramiding increased return in this single-stock, one-year sample, but it also pushed the best configurations very close to full capital usage.
- The best-return result is again concentrated at the highest tested exposure, so it should not be treated as robust without cross-symbol and walk-forward validation.
- The next implementation step should add equivalent pyramiding support in Backtrader for order-level validation, including A-share lot size, rejected orders, and more realistic cash constraints.
