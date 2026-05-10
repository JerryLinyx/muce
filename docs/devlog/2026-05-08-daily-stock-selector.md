# 2026-05-08 Daily Stock Selector

## Prompt Context

After building the data layer, Backtrader validation, VectorBT research sweep, and technical indicator layer, the next requirement was a daily full-market selector.

The selector should combine factors such as:

```text
moving-average breakout
KDJ golden cross
MACD golden cross
RSI momentum
volume breakout
Bollinger-band breakout
```

It should produce daily candidates and support backtesting candidate selection.

## Indicator Oracle Choice

Added optional TA-Lib support:

```toml
[project.optional-dependencies]
indicators = ["ta-lib>=0.6.8"]
```

Rationale:

- TA-Lib is a common industry reference for technical indicators.
- It has prebuilt wheels for current Python/macOS/Linux combinations on PyPI.
- It remains optional because the core system should not depend on native indicator packages.

Added:

```text
src/quant_backtest/features/talib_oracle.py
tests/test_talib_oracle.py
```

If TA-Lib is not installed, oracle tests are skipped. In the current environment, TA-Lib was not installed, so the result was:

```text
2 skipped
```

## Selector Implementation

Added:

```text
src/quant_backtest/selection/__init__.py
src/quant_backtest/selection/factors.py
src/quant_backtest/selection/backtest.py
src/quant_backtest/cli_selection.py
```

CLI entry:

```bash
quant-select
```

Commands:

```bash
quant-select candidates
quant-select backtest
```

The selector builds a per-symbol, per-date factor table and then ranks candidates by:

```text
factor_score desc
amount desc
volume desc
symbol asc
```

Current factor definitions:

```text
ma_breakout:
  close crosses above MA(short), with MA(short) > MA(long)

kdj_golden_cross:
  K crosses above D

macd_golden_cross:
  MACD diff crosses above DEA

rsi_momentum:
  RSI >= threshold

volume_breakout:
  volume >= volume MA * multiplier

boll_breakout:
  close crosses above upper Bollinger band
```

The selector excludes suspended and ST rows by default when those columns are available.

## Selector Backtest

`run_selection_backtest()` uses:

```text
qfq bars for factor/signals
raw close for execution
VectorBT Portfolio.from_signals
cash_sharing=True
fixed hold_days exit
```

This is a research-level backtest. Backtrader order-level validation should be added later for top selector rules.

## Real Cache Smoke Test

With the current one-symbol cache:

```bash
uv run quant-select candidates \
  --symbols 603986.SH \
  --start 20250507 \
  --end 20260507 \
  --min-score 1 \
  --top-n 5
```

Result:

```text
candidate_count: 1
symbol: 603986.SH
date: 2026-05-07
factor_score: 1
factor_reasons: rsi_momentum
```

Backtest smoke command:

```bash
uv run quant-select backtest \
  --symbols 603986.SH \
  --start 20250507 \
  --end 20260507 \
  --min-score 1 \
  --top-n 1 \
  --hold-days 2 \
  --target-percent-per-position 50 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5
```

Result:

```text
final_value: 999600.24
total_return: -0.03998%
candidate_count: 1
entry_count: 1
trade_count: 1
```

This result is only a smoke test because the cache currently has one symbol.

## Full-Market Selector Function Test

After the one-year full-market cache was downloaded, ran the selector on:

```text
universe: 5200 A-share symbols
signal data: qfq
execution data: raw
date range: 2025-05-07 to 2026-05-07
```

For latest-day candidate inspection on `2026-05-07`, with:

```text
min_score: 2
top_n: 50
```

Result:

```text
eligible candidates before top_n: 1195
top_n returned: 50
score distribution:
  6: 3
  5: 7
  4: 58
  3: 266
  2: 861
```

Factor hits among all `min_score >= 2` selected names on that date:

```text
ma_breakout: 67
kdj_golden_cross: 446
macd_golden_cross: 186
rsi_momentum: 1088
volume_breakout: 659
boll_breakout: 359
```

Observation:

- `min_score=2` is too broad for a concentrated daily selector because it admitted 1195 names.
- `min_score=4` is closer to the desired "dozens of names" behavior. On `2026-05-07`, it selected 68 names before top-N truncation.

Top latest-day candidates under `min_score=4` included:

```text
601868.SH score=6
300955.SZ score=6
688055.SH score=6
688167.SH score=5
601669.SH score=5
300913.SZ score=5
603997.SH score=5
301000.SZ score=5
600207.SH score=5
002951.SZ score=5
```

## Backtest Semantics Fix

The first selector backtest implementation used the candidate date directly as the entry date. Since the selector factors use same-day close, that creates look-ahead risk if the strategy is interpreted as "screen after close, then trade".

Changed selector backtest semantics:

```text
candidate date: compute factors using qfq close
entry_lag_days: default 1
entry date: next trading bar
exit: entry shifted by hold_days
```

Added CLI option:

```bash
--entry-lag-days
```

This keeps the MVP closer to a realistic daily workflow:

```text
after market close -> screen candidates -> trade on next bar
```

## Full-Market Selector Backtest Smoke

Command:

```bash
uv run quant-select backtest \
  --start 20250507 \
  --end 20260507 \
  --min-score 4 \
  --top-n 50 \
  --hold-days 1 \
  --entry-lag-days 1 \
  --target-percent-per-position 2 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5
```

Result:

```text
candidate_count: 9414
entry_count: 9364
trade_count: 9288
final_value: 994,823.48
total_return: -0.52%
annual_return: -0.54%
max_drawdown: 14.80%
sharpe: -0.01
```

Interpretation:

- Functionally, the full-market selector and vectorized selector backtest work end to end.
- The initial factor set is not yet a good alpha model under this realistic one-bar entry lag.
- `min_score=4` produces a usable candidate count, but the scoring model is still a simple unweighted vote.
- The next step should be factor attribution and parameter sweeps before relying on this selector.

## Tests

Added:

```text
tests/test_selection.py
tests/test_talib_oracle.py
```

Verification:

```bash
uv run pytest
```

Result:

```text
40 passed, 2 skipped
```

## Next Questions

- Download a full A-share or sector universe before interpreting selector results.
- Add liquidity filters such as minimum amount, minimum price, and maximum ST/suspension exclusions.
- Add factor weights instead of simple additive scoring.
- Add Backtrader validation for top selector candidates.
- Add feature-store persistence so full-market factor tables do not need to be recomputed every run.

## Selector Hit-Rate Validation

Added a separate hit-rate validation path:

```text
src/quant_backtest/selection/hit_rate.py
quant-select hit-rate
quant-select sweep-hit-rate
```

Purpose:

```text
Daily close-time selection: choose top N names.
Next-day label: raw next close > raw current close is a win.
```

This is intentionally separate from portfolio backtesting. It answers whether the factor stack predicts next-day direction, not whether a specific cash/position-sizing rule makes money.

Baseline command:

```bash
uv run quant-select hit-rate \
  --start 20250507 \
  --end 20260507 \
  --min-score 4 \
  --top-n 10 \
  --forward-days 1 \
  --daily-limit 10
```

Baseline result:

```text
signal_days: 223
total_signals: 2223
valid_signals: 2213
invalid_signals: 10
win_count: 1024
loss_count: 1156
flat_count: 33
win_rate: 46.27%
avg_daily_win_rate: 46.25%
positive_day_rate: 56.50%
avg_forward_return: 0.37%
median_forward_return: -0.27%
```

The final date `2026-05-07` has invalid next-day labels because the cache currently ends on that date.

Small parameter sweep:

```bash
uv run quant-select sweep-hit-rate \
  --start 20250507 \
  --end 20260507 \
  --top-n-list 10,20,50 \
  --min-score-list 3,4,5 \
  --rsi-threshold-list 55 \
  --volume-multiplier-list 1.5 \
  --forward-days 1 \
  --limit 12
```

Best row in this small grid:

```text
top_n: 50
min_score: 5
valid_signals: 2604
win_rate: 46.62%
avg_daily_win_rate: 46.67%
avg_forward_return: 0.46%
median_forward_return: -0.18%
```

Interpretation:

- The current unweighted technical-factor voting selector is not a validated positive-direction factor.
- Higher strictness slightly improved this small grid, but still stayed below 50% win rate.
- Average next-day return is positive while median is negative, which suggests a few larger winners are lifting the mean.
- Next work should inspect factor contribution, industry/size/liquidity effects, and walk-forward robustness instead of selecting the best row from a small in-sample sweep.

## Strict Factor Attribution

Added hard selector filters:

```text
require_factors
exclude_factors
--require-factors
--exclude-factors
```

Added attribution command:

```bash
quant-select attribution
```

It reports:

```text
by_combo
by_score
by_factor
```

During implementation, `sweep-hit-rate` was found to overwrite the selector's original `selected` mask when changing `min_score`, which accidentally ignored `require_factors` and `exclude_factors`. Fixed by preserving the base selection mask and only tightening the score threshold.

Full-market attribution command:

```bash
uv run quant-select attribution \
  --start 20250507 \
  --end 20260507 \
  --min-score 3 \
  --top-n 5000 \
  --forward-days 1 \
  --min-valid-count 80 \
  --limit 20
```

Best exact factor combination:

```text
kdj_golden_cross,macd_golden_cross,rsi_momentum,boll_breakout
valid_count: 345
win_rate: 57.68%
avg_forward_return: 1.76%
median_forward_return: 0.48%
```

Single-factor attribution showed:

```text
ma_breakout:      win_rate 48.08%, median  0.00%
kdj_golden_cross: win_rate 47.03%, median -0.13%
macd_golden_cross:win_rate 45.40%, median -0.21%
rsi_momentum:     win_rate 45.11%, median -0.24%
boll_breakout:    win_rate 44.70%, median -0.28%
volume_breakout:  win_rate 44.12%, median -0.31%
```

Important interpretation:

- The individual factors are weak by themselves.
- The useful behavior appears in a specific interaction: KDJ cross + MACD cross + RSI momentum + Bollinger breakout.
- `volume_breakout` is currently a drag in the one-day label setup.

Strict rule tested:

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

Close-to-next-close hit-rate result:

```text
top_n=1:
  valid_signals: 135
  win_rate: 64.44%
  avg_forward_return: 2.41%
  median_forward_return: 0.99%

top_n=2:
  valid_signals: 215
  win_rate: 60.00%
  avg_forward_return: 2.07%
  median_forward_return: 0.80%

top_n=5:
  valid_signals: 295
  win_rate: 58.31%
  avg_forward_return: 1.94%
  median_forward_return: 0.56%
```

More conservative next-open-to-next-close result:

```text
top_n=1:
  valid_signals: 135
  win_rate: 50.37%
  avg_forward_return: 0.81%
  median_forward_return: 0.02%

top_n=2:
  win_rate: 47.44%

top_n=5:
  win_rate: 45.42%
```

This suggests a meaningful portion of the edge comes from the close-to-next-day path, possibly overnight movement. If the system cannot trade near the signal close, this rule should be heavily discounted.

Portfolio smoke tests using the strict rule, `top_n=1`, 100% target allocation, 3 bps commission, and 5 bps slippage:

```text
entry_lag_days=0:
  total_return: 494.10%
  max_drawdown: 18.61%
  sharpe: 3.21

entry_lag_days=1:
  total_return: 117.23%
  max_drawdown: 33.66%
  sharpe: 1.64
```

These portfolio results are not deployment-ready because they use one-stock full allocation and simplified close-price execution. They justify deeper validation, not live trading.

## Execution-Aware Selector Simulation

Added an execution-aware selector simulator:

```text
src/quant_backtest/selection/execution.py
quant-select simulate
```

The simulator models:

```text
fixed holding days
entry lag
open/close entry price choice
open/close exit price choice
target percent per position
max concurrent positions
100-share lot-size rounding
commission
base slippage
extra slippage after sharp entry-day surge
limit-up buy rejection
limit-down sell rejection
cash/lot insufficiency rejection
```

Conservative defaults:

```text
reject_limit_up_buy: true
reject_limit_down_sell: true
lot_size: 100
surge_threshold_pct: 3%
surge_extra_slippage_bps: 20
```

Strict factor rule:

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

Simulation 1:

```bash
uv run quant-select simulate \
  --start 20250507 \
  --end 20260507 \
  --min-score 4 \
  --top-n 1 \
  --require-factors kdj_golden_cross,macd_golden_cross,rsi_momentum,boll_breakout \
  --exclude-factors ma_breakout,volume_breakout \
  --hold-days 1 \
  --entry-lag-days 0 \
  --entry-price-field close \
  --exit-price-field close \
  --target-percent-per-position 20 \
  --max-positions 1 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5 \
  --surge-threshold-pct 3 \
  --surge-extra-slippage-bps 20
```

Result:

```text
total_return: 6.47%
annual_return: 6.74%
max_drawdown: 4.94%
sharpe: 0.85
filled_buy_count: 67
filled_sell_count: 66
rejected_buy_count: 69
limit_up_buy_rejections: 69
limit_down_sell_rejections: 0
trade_win_rate: 51.52%
```

Interpretation:

- The earlier close-to-next-close result was heavily affected by candidates that were already at or near limit-up.
- Once limit-up buys are rejected, many attractive-looking signals are not executable.

Simulation 2:

```text
entry_lag_days: 1
entry_price_field: open
exit_price_field: close
hold_days: 1
target_percent_per_position: 20%
max_positions: 1
```

Result:

```text
total_return: 31.89%
annual_return: 33.41%
max_drawdown: 10.05%
sharpe: 1.90
filled_buy_count: 122
filled_sell_count: 122
rejected_buy_count: 13
rejected_sell_count: 5
limit_up_buy_rejections: 10
limit_down_sell_rejections: 5
trade_win_rate: 55.74%
```

Simulation 3:

```text
entry_lag_days: 1
entry_price_field: open
exit_price_field: close
hold_days: 2
target_percent_per_position: 20%
max_positions: 1
```

Result:

```text
total_return: 31.03%
annual_return: 32.50%
max_drawdown: 7.60%
sharpe: 2.01
filled_buy_count: 73
filled_sell_count: 72
rejected_buy_count: 62
rejected_sell_count: 1
limit_up_buy_rejections: 6
limit_down_sell_rejections: 1
trade_win_rate: 62.50%
```

Interpretation:

- Holding 2 days had similar return to holding 1 day, but lower drawdown and higher trade win rate in this one-year sample.
- Holding 2 days also skipped many new signals because `max_positions=1` kept capital occupied.
- Current best research direction is not "maximize holding days"; it is to sweep `hold_days`, `target_percent_per_position`, and `max_positions` together under execution constraints.
- Limit-up/limit-down handling is mandatory for this selector. Without it, the result is too optimistic.

## Execution Sweep For Close-Time Selector

Added execution sweep command:

```bash
quant-select sweep-simulate
```

It reuses one full-market data load and one factor table, then sweeps execution parameters:

```text
hold_days
target_percent_per_position
max_positions
top_n
entry_lag_days
stop_loss_pct
take_profit_pct
```

During the first run, performance was too slow because each parameter combination rebuilt the full `(date, symbol)` raw-bar index from 1.25M rows. Refactored the simulator to build an `ExecutionSimulationContext` once per sweep and reuse it across all combinations.

First sweep:

```bash
uv run quant-select sweep-simulate \
  --start 20250507 \
  --end 20260507 \
  --min-score 4 \
  --require-factors kdj_golden_cross,macd_golden_cross,rsi_momentum,boll_breakout \
  --exclude-factors ma_breakout,volume_breakout \
  --entry-lag-days-list 0 \
  --entry-price-field close \
  --exit-price-field close \
  --hold-days-list 1,2,3,4,5 \
  --target-percent-list 5,10,20,30 \
  --max-positions-list 1,2,3,5 \
  --top-n-list 1,2,5 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5 \
  --surge-threshold-pct 3 \
  --surge-extra-slippage-bps 20 \
  --rank-by sharpe \
  --limit 20
```

Best Sharpe row:

```text
hold_days: 5
target_percent_per_position: 30%
max_positions: 1
top_n: 5
stop_loss_pct: none
take_profit_pct: none
total_return: 40.90%
annual_return: 42.91%
max_drawdown: 7.94%
sharpe: 2.16
filled_buy_count: 34
limit_up_buy_rejections: 32
trade_win_rate: 75.76%
```

Observation:

- The best region was not 1-day holding.
- Strong rows clustered around `hold_days=5`, `max_positions=1`, and `top_n=5`.
- Increasing position size improved return but also increased drawdown. The 20% version had similar Sharpe with lower drawdown.

Second sweep added stop-loss/take-profit around the best region:

```bash
uv run quant-select sweep-simulate \
  --start 20250507 \
  --end 20260507 \
  --min-score 4 \
  --require-factors kdj_golden_cross,macd_golden_cross,rsi_momentum,boll_breakout \
  --exclude-factors ma_breakout,volume_breakout \
  --entry-lag-days-list 0 \
  --entry-price-field close \
  --exit-price-field close \
  --hold-days-list 3,4,5 \
  --target-percent-list 20,30 \
  --max-positions-list 1 \
  --top-n-list 2,5 \
  --stop-loss-list none,-5,-10 \
  --take-profit-list none,5,10,20 \
  --cash 1000000 \
  --commission-bps 3 \
  --slippage-bps 5 \
  --surge-threshold-pct 3 \
  --surge-extra-slippage-bps 20 \
  --rank-by sharpe \
  --limit 20
```

Best Sharpe row:

```text
hold_days: 5
target_percent_per_position: 30%
max_positions: 1
top_n: 5
stop_loss_pct: none
take_profit_pct: 20%
total_return: 55.14%
annual_return: 57.98%
max_drawdown: 7.95%
sharpe: 2.63
filled_buy_count: 35
limit_up_buy_rejections: 32
trade_win_rate: 70.59%
```

More conservative variant:

```text
hold_days: 5
target_percent_per_position: 20%
max_positions: 1
top_n: 5
stop_loss_pct: none
take_profit_pct: 20%
total_return: 34.10%
annual_return: 35.74%
max_drawdown: 5.34%
sharpe: 2.63
filled_buy_count: 35
limit_up_buy_rejections: 32
trade_win_rate: 70.59%
```

Current recommendation for the next validation candidate:

```text
entry_lag_days: 0
entry_price_field: close
exit_price_field: close
hold_days: 5
top_n: 5
max_positions: 1
target_percent_per_position: 20%
take_profit_pct: 20%
stop_loss_pct: none for now
limit-up buy rejection: enabled
limit-down sell rejection: enabled
base slippage: 5 bps
surge extra slippage: +20 bps after 3% entry-day rise
```

This is still a daily-bar approximation of close-time buying. It should not be treated as proof that tail execution is available at the close price. The next step is either minute data or a Backtrader execution validation with more conservative fill assumptions.

## Backtrader Selector Validation

Added Backtrader validation for precomputed selector signals:

```text
src/quant_backtest/selection/backtrader_validation.py
quant-select validate-backtrader
get_precomputed_selector_strategy_class()
```

Design:

- The selector still computes factor candidates from qfq data.
- Only symbols that appear in the candidate table are loaded into Backtrader.
- The Backtrader strategy consumes precomputed signal dates instead of recalculating factors.
- Backtrader handles broker cash, orders, positions, commission, slippage, and trade/equity analyzers.
- Limit-up buy and limit-down sell rejection are checked before submitting orders.

Important semantic difference:

- The execution simulator can use daily `high` to trigger take-profit.
- The Backtrader selector validation currently uses a more conservative close-confirmed take-profit: sell only when close reaches the threshold.

Recommended sweep candidate:

```text
top_n: 5
hold_days: 5
target_percent_per_position: 20%
max_positions: 1
take_profit_pct: 20%
stop_loss_pct: none
execution_timing: same_close
```

Backtrader result with close-confirmed 20% take-profit:

```text
candidate_count: 300
validation_symbol_count: 281
total_return: 20.37%
annual_return: 21.30%
max_drawdown: 4.85%
sharpe: 1.94
order_count: 58
trade_count: 29
```

Backtrader result without take-profit:

```text
candidate_count: 300
validation_symbol_count: 281
total_return: 25.11%
annual_return: 26.28%
max_drawdown: 4.85%
sharpe: 2.33
order_count: 56
trade_count: 28
```

Backtrader next-open result without take-profit:

```text
candidate_count: 300
validation_symbol_count: 281
total_return: 19.18%
annual_return: 20.04%
max_drawdown: 5.51%
sharpe: 1.78
order_count: 56
trade_count: 28
```

Interpretation:

- Backtrader without take-profit is close to the simulator no-take-profit row, so the signal and holding mechanics cross-check reasonably.
- The simulator's `take_profit_pct=20%` improvement is partly due to optimistic daily-high take-profit semantics.
- Under the more conservative close-confirmed Backtrader semantics, the 20% take-profit is not better than no take-profit.
- The next validation target should therefore be:

```text
top_n: 5
hold_days: 5
target_percent_per_position: 20%
max_positions: 1
take_profit_pct: none
stop_loss_pct: none
```

This candidate remains positive under same-close and next-open Backtrader validation, but it still needs minute-level data before claiming true tail-close executability.

## Layered Selector Sweep

Added factor-parameter layering to `quant-select sweep-simulate`:

```text
--min-score-list
--rsi-threshold-list
--volume-multiplier-list
--boll-std-list
```

The sweep result rows now include the factor layer parameters alongside execution parameters. This makes it possible to compare factor thresholds and execution settings in one table instead of running multiple manual commands.

Layer 1 expanded execution parameters while keeping the strict factor rule fixed:

```text
require: kdj_golden_cross, macd_golden_cross, rsi_momentum, boll_breakout
exclude: ma_breakout, volume_breakout
entry: same-day raw close
hold_days: 3,4,5,6,7,8,9,10
target_percent: 10%,15%,20%,25%,30%
max_positions: 1,2
top_n: 3,5,8,10
take_profit/stop_loss: none
```

Best same-close execution cluster:

```text
hold_days: 10
target_percent_per_position: 20%
max_positions: 2
top_n: 3
total_return: 54.25%
annual_return: 57.04%
max_drawdown: 7.63%
sharpe: 2.52
filled_buy_count: 37
trade_win_rate: 62.86%
candidate_count: 259
```

Layer 1 next-open pressure test around the same area:

```text
entry: next-day raw open
hold_days: 8,10,12
target_percent: 10%,15%,20%,25%,30%
max_positions: 1,2
top_n: 3,5
```

Best next-open simulator cluster:

```text
hold_days: 10
target_percent_per_position: 30%
max_positions: 1
top_n: 3 or 5
total_return: 62.11%
annual_return: 65.38%
max_drawdown: 13.91%
sharpe: 2.44
filled_buy_count: 20
trade_win_rate: 52.63%
candidate_count: 259
```

Layer 2 added factor thresholds:

```text
rsi_threshold: 50,55,60,65,70
boll_std: 1.5,2.0,2.5
hold_days: 8,10,12
target_percent: 15%,20%,25%
max_positions: 1,2
top_n: 3,5
entry: same-day raw close
```

The strongest same-close rows all used `boll_std=1.5`. Two parameter regions emerged:

```text
Region A:
  rsi_threshold: 70
  boll_std: 1.5
  hold_days: 10
  target_percent_per_position: 20%
  max_positions: 1
  top_n: 3 or 5
  total_return: 44.26%
  max_drawdown: 4.24%
  sharpe: 3.40
  filled_buy_count: 16
  trade_win_rate: 66.67%
  candidate_count: 138

Region B:
  rsi_threshold: 50 or 55
  boll_std: 1.5
  hold_days: 12
  target_percent_per_position: 15%
  max_positions: 1
  top_n: 3 or 5
  total_return: 35.23%
  max_drawdown: 2.87%
  sharpe: 3.40
  filled_buy_count: 17
  trade_win_rate: 75.00%
  candidate_count: 462-643
```

Layer 3 next-open pressure test:

```text
rsi_threshold: 50,55,70
boll_std: 1.5
hold_days: 10,12
target_percent: 15%,20%,25%
max_positions: 1,2
top_n: 3
entry: next-day raw open
```

The `rsi_threshold=70, boll_std=1.5, hold_days=10` region survived best:

```text
target_percent_per_position: 20%
max_positions: 2
total_return: 66.60%
annual_return: 70.15%
max_drawdown: 7.37%
sharpe: 2.70
filled_buy_count: 33
trade_win_rate: 56.25%
candidate_count: 138
```

However, Backtrader validation materially reduced the result for the same parameters:

```text
rsi_threshold: 70
boll_std: 1.5
top_n: 3
hold_days: 10
target_percent_per_position: 20%
max_positions: 2
take_profit_pct: none
stop_loss_pct: none

Backtrader next_open:
  total_return: 30.45%
  annual_return: 31.89%
  max_drawdown: 9.03%
  sharpe: 1.89
  order_count: 51
  trade_count: 25
  candidate_count: 138
  validation_symbol_count: 134

Backtrader same_close:
  total_return: 30.48%
  annual_return: 31.93%
  max_drawdown: 9.32%
  sharpe: 1.88
  order_count: 51
  trade_count: 25
```

Interpretation:

- `boll_std=1.5` is currently the best strict breakout threshold in the one-year sample.
- `rsi_threshold=70` is more robust to next-open execution than `50/55`, but it has fewer trades.
- The execution simulator is still optimistic relative to Backtrader for this layered candidate.
- For research reporting, the current conservative candidate should be described by the Backtrader result, not the simulator result.
- The current Pandas path is too slow for broad multi-factor sweeps because full-market indicator tables are recomputed for each factor threshold layer. The next performance improvement should cache factor tables or materialize an indicator layer.

Current conservative validation candidate:

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
execution reference: Backtrader same_close/next_open around 30% total return, Sharpe around 1.9
```
