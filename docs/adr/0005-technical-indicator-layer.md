# ADR 0005: Technical Indicator Layer

## Status

Accepted

## Context

The project needs common technical indicators such as MA, EMA, MACD, KDJ, RSI, Bollinger Bands, ATR, volume moving averages, and OBV. These values are derived features, not raw market data.

Data vendors may provide some precomputed indicators, and frameworks such as Backtrader and VectorBT also provide indicator utilities. Relying directly on either source in strategy code would make the calculation semantics harder to audit and harder to keep consistent across research and validation backends.

## Decision

Introduce a separate feature layer under `quant_backtest.features`.

Raw data remains limited to standardized OHLCV and metadata. Technical indicators are computed from cached qfq/raw bars through a project-owned interface:

```python
from quant_backtest.features import add_technical_indicators
```

Core implementation uses pandas only, with no required runtime dependency. TA-Lib is introduced as an optional oracle dependency for cross-checking selected formulas:

```toml
indicators = ["ta-lib>=0.6.8"]
```

Supported first-version indicators:

```text
MA
EMA
MACD
KDJ
RSI
Bollinger Bands
ATR
Volume MA
OBV
```

Indicators are computed independently per `symbol` when a `symbol` column is present.

## Rationale

- Keep raw market data cache clean and vendor-auditable.
- Avoid coupling strategy code to vendor-provided indicator fields.
- Avoid making TA-Lib a required dependency before we need its larger indicator catalog.
- Keep calculation semantics testable and documented.
- Preserve the option to swap the implementation behind the feature interface later.

## Indicator Semantics

Current pandas implementation uses these conventions:

```text
MA: rolling simple moving average with min_periods=window
EMA: pandas ewm(span=window, adjust=False, min_periods=window)
MACD: EMA(fast) - EMA(slow), signal EMA on diff, histogram diff - signal
RSI: Wilder-style smoothing via ewm(alpha=1/window, adjust=False)
KDJ: RSV over rolling high/low, recursive K/D smoothing with initial value 50
BOLL: rolling mean plus/minus num_std * population std, ddof=0
ATR: Wilder-style smoothing of true range via ewm(alpha=1/window, adjust=False)
OBV: cumulative signed volume based on close-to-close direction
```

## Consequences

- Strategies should call the feature layer instead of importing TA-Lib, pandas-ta, or VectorBT indicators directly.
- If a mature package is introduced later, it should be wrapped behind the same interface.
- Indicator outputs are not yet cached as a versioned feature store. That remains a future task.
- TA-Lib comparison tests are skipped when the optional `indicators` extra is not installed.
