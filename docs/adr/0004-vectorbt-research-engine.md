# ADR 0004: VectorBT Research Engine

## Status

Accepted

## Context

The project needs a fast research layer to test parameter variants before promoting candidates into deeper Backtrader validation. Backtrader is useful for event-driven validation, but it is not the right tool for broad parameter sweeps.

## Decision

Add a dedicated VectorBT research engine with:

- `VectorbtConfig`
- `VectorbtResult`
- `VectorbtSignals`
- `VectorbtEngine`
- strategy signal builders
- parameter grid expansion
- CLI `quant-backtest sweep`

The engine uses:

```text
qfq panels for signal generation
raw close panels for vectorized execution prices
```

Supported v1 sweep strategies:

- `sma-cross`
- `three-rising-hold-one`
- `three-falling-buy-three-rising-sell`

## Reasoning

VectorBT is designed around pandas/NumPy arrays and is a natural fit for fast experiments. It allows the project to quickly reject weak parameter choices before using Backtrader for detailed order logs and validation.

The research engine intentionally returns normalized metric rows rather than exposing only raw VectorBT objects. This keeps CLI output and later pipeline integration simple.

## Consequences

Positive:

- Parameter sweeps are now a first-class workflow.
- The same cached qfq/raw data semantics are reused.
- Sweep output can be ranked by `total_return`, `sharpe`, `max_drawdown`, or trade metrics.

Tradeoffs:

- VectorBT execution semantics are less detailed than Backtrader.
- Current VectorBT module uses close-to-close vectorized execution and should be treated as research, not final validation.
- Current strategy builders are duplicated conceptually with Backtrader strategy classes; a shared strategy spec should reduce this later.
- Even after metric normalization, fee and slippage handling can differ slightly from Backtrader. No-cost runs should match; costed runs should be checked within tolerance.

## Follow-Up Work

- Export sweep results to Parquet/CSV.
- Add a pipeline that sends top-N sweep candidates into Backtrader validation.
- Add multi-symbol portfolio sweeps with cash sharing policy explicitly configured.
- Add factor IC and grouped-return analysis separate from trade simulation.
- Watch VectorBT/pandas 3 compatibility warnings and pin versions if needed.
- Add a formal cross-engine report command for validating candidate strategies before promotion.
