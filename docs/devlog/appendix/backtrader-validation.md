# Backtrader Validation Guide

## Purpose

The backtrader validation module is the first deeper event-driven validation layer. It is intended to run candidate strategies after faster research or parameter sweeps.

It is not intended to replace vectorized research. Its job is to validate candidates under clearer execution assumptions, cost assumptions, and order logs.

## Data Semantics

The module uses two price views:

```text
qfq signal data -> indicators and trading signals
raw execution data -> broker fills and portfolio value
```

Default settings:

```text
signal_adjust=qfq
execution_adjust=raw
execution_timing=next_open
```

The custom backtrader feed exposes raw OHLCV as standard lines:

```text
open
high
low
close
volume
```

It also exposes qfq signal fields:

```text
signal_open
signal_high
signal_low
signal_close
signal_volume
```

Strategy code should use `signal_*` for adjusted indicators and normal OHLC lines for execution-aware logic.

## Run The Built-In Strategy

First ensure qfq and raw data are cached for the same symbol and date range:

```bash
uv run quant-data download --symbols 000001.SZ --start 20200101 --end 20251231 --adjust qfq
uv run quant-data download --symbols 000001.SZ --start 20200101 --end 20251231 --adjust raw
```

Then run validation:

```bash
uv run quant-backtest validate \
  --symbols 000001.SZ \
  --signal-adjust qfq \
  --execution-adjust raw \
  --execution-timing next_open \
  --fast-period 5 \
  --slow-period 20
```

Run the three-rising one-day MVP factor:

```bash
uv run quant-backtest validate \
  --symbols 603986.SH \
  --strategy three-rising-hold-one \
  --signal-adjust qfq \
  --execution-adjust raw \
  --execution-timing same_close \
  --target-percent 0.95 \
  --hold-bars 1
```

Run the three-falling buy / three-rising sell MVP factor:

```bash
uv run quant-backtest validate \
  --symbols 603986.SH \
  --strategy three-falling-buy-three-rising-sell \
  --signal-adjust qfq \
  --execution-adjust raw \
  --execution-timing same_close \
  --target-percent 0.95 \
  --signal-count 3
```

## Python API

```python
from quant_backtest.backtest import (
    BacktraderConfig,
    BacktraderEngine,
    get_signal_sma_cross_strategy_class,
)
from quant_backtest.data.cache import ParquetCache

cache = ParquetCache("data/cache/a_share/daily")
config = BacktraderConfig(
    symbols=["000001.SZ"],
    cash=1_000_000,
    commission_bps=3,
    slippage_bps=5,
    signal_adjust="qfq",
    execution_adjust="raw",
    execution_timing="next_open",
    strategy_kwargs={
        "fast_period": 5,
        "slow_period": 20,
        "target_percent": 0.95,
    },
)

result = BacktraderEngine(cache).run(
    get_signal_sma_cross_strategy_class(),
    config,
)

print(result.metrics)
print(result.equity_curve.tail())
print(result.orders.tail())
```

## Current Output

`BacktraderResult` contains:

- `metrics`
- `equity_curve`
- `orders`
- `trades`
- `raw_analyzers`
- `final_value`
- `start_cash`

Use `to_frames()` to get a dictionary of pandas DataFrames.

## Known Limitations

- No CLI `--out` export yet.
- No daily position analyzer yet.
- No A-share lot-size, T+1, suspension, or limit-up/limit-down modeling yet.
- The built-in SMA strategy is only an example, not the final strategy interface.

## VectorBT Research Companion

Use VectorBT for fast parameter screening before Backtrader validation:

```bash
uv run quant-backtest sweep \
  --symbols 603986.SH \
  --strategy three-falling-buy-three-rising-sell \
  --signal-counts 2,3,4 \
  --rank-by total_return
```

Treat VectorBT output as research ranking. Use Backtrader for final validation because Backtrader gives more explicit order and execution logs.

For cross-engine checks, compare normalized metrics from the equity curve. No-cost runs should match exactly. With costs enabled, expect very small differences because Backtrader and VectorBT do not apply sizing, fees, and slippage through identical broker logic.