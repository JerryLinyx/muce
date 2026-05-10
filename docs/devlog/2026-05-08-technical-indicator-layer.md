# 2026-05-08 Technical Indicator Layer

## Prompt Context

We clarified that market data providers should mainly provide raw market data, while indicators should be computed by a dedicated feature layer or by framework utilities wrapped behind project-owned interfaces.

Important design points:

- Do not store MA/KDJ/MACD/RSI directly in the raw OHLCV cache.
- Keep data source, feature calculation, strategy logic, and execution engine as separate layers.
- Use mature libraries when useful, but keep strategy code independent from direct library calls.
- Document indicator formula choices because different libraries can disagree on warmup, smoothing, and missing-value behavior.

## Implementation

Added `quant_backtest.features` with a pandas-only first implementation:

```text
src/quant_backtest/features/__init__.py
src/quant_backtest/features/indicators.py
```

The unified entry point is:

```python
add_technical_indicators(frame, config=TechnicalIndicatorConfig())
```

Implemented indicators:

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

The function computes indicators independently per symbol if the input contains a `symbol` column. This prevents one symbol's rolling window from leaking into another symbol's feature rows.

## Formula Choices

The first version uses explicit pandas formulas:

```text
MA: rolling simple moving average
EMA: ewm(span=window, adjust=False)
MACD: EMA fast/slow diff, EMA signal, diff-signal histogram
RSI: Wilder-style ewm alpha=1/window
KDJ: RSV rolling window, K/D recursive smoothing with initial 50
BOLL: rolling mean and population std
ATR: true range with Wilder-style smoothing
OBV: cumulative signed volume
```

These choices are now locked by tests. If we later compare against TA-Lib, pandas-ta, or VectorBT indicators, differences should be treated as formula differences first, not automatically as bugs.

## Tests

Added `tests/test_indicators.py` covering:

- Moving averages and volume moving averages.
- MACD, RSI, Bollinger Bands, and OBV outputs.
- KDJ initial value and recursive smoothing behavior.
- Per-symbol isolation.
- Feature-only output mode.
- Required OHLCV column validation.

Verification:

```bash
uv run pytest tests/test_indicators.py
```

Result:

```text
6 passed
```

## Cross-Source Check

After implementation, we compared selected indicators against local VectorBT `0.28.2` on cached `603986.SH` qfq daily bars.

Results:

```text
MA20:  max_abs_diff ~= 4.55e-13
EMA12: max_abs_diff ~= 5.68e-14
BOLL:  max_abs_diff ~= 2.10e-11
```

These match VectorBT to floating-point tolerance.

MACD matched VectorBT only when VectorBT was called with:

```python
vbt.MACD.run(close, macd_ewm=True, signal_ewm=True)
```

With those settings:

```text
MACD diff max_abs_diff ~= 1.14e-13
MACD signal max_abs_diff ~= 5.86e-14
```

VectorBT default MACD differs because its default smoothing settings are not the same as our documented EMA-based MACD.

RSI and ATR differed from VectorBT defaults and from VectorBT `ewm=True` runs. This is expected until we choose a specific external reference because RSI/ATR implementations vary by smoothing method, warmup, and initialization. Our current implementation uses Wilder-style smoothing via:

```text
ewm(alpha=1/window, adjust=False, min_periods=window)
```

Conclusion:

- The simple rolling indicators and EMA-based MACD are cross-validated against VectorBT.
- RSI and ATR are formula-locked by internal tests but not yet externally validated against a chosen oracle.
- A future task should compare RSI/ATR/KDJ against TA-Lib or pandas-ta and decide whether to match that oracle or preserve the current A-share-style formula.

## Open Questions

- Whether to add a persisted feature store under `data/features/a_share/daily`.
- Whether to add `quant-features build` and `quant-features inspect` CLI commands.
- Whether to compare our formulas against TA-Lib/pandas-ta/vectorbt for selected indicators.
- Whether to add A-share-specific volume features, such as volume ratio, turnover change, amount moving average, and limit-up/limit-down context.
