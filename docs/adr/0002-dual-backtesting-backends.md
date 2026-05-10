# ADR 0002: Dual Backtesting Backends

## Status

Accepted

## Context

The project needs both fast research iteration and more realistic validation.

Options considered:

- Build a fully custom backtesting engine.
- Use only `backtrader`.
- Use only `vectorbt`.
- Use `vectorbt` for sweeps and `backtrader` for validation.

## Decision

Use a dual-backend model:

- `vectorbt` for fast parameter sweeps and signal research.
- `backtrader` for event-driven validation.

Keep both as optional extras rather than mandatory core dependencies.

## Reasoning

`vectorbt` is aligned with pandas/NumPy arrays and wide panels. It is a good fit for fast parameter sweeps, factor experiments, and broad candidate filtering.

`backtrader` is aligned with strategy classes, data feeds, broker simulation, orders, commissions, slippage, and analyzers. It is a good fit for deeper validation of candidate strategies after sweep.

The engines have different natural data shapes:

- vectorbt prefers wide frames: `index=date`, `columns=symbol`.
- backtrader prefers per-symbol feeds with OHLCV lines.

Forcing a single shape across both would make the implementation harder to reason about. The project therefore uses adapters rather than a universal DataFrame.

## Consequences

Positive:

- Research can stay fast.
- Validation can be more realistic.
- The data layer remains shared and testable.
- Strategy candidates can flow from sweep to validation later.

Tradeoffs:

- Two framework APIs must be maintained.
- Strategy definitions need a mapping or wrapper layer if the same idea should run in both engines.
- Dependency licensing and installation need to remain explicit.

## Follow-Up Work

- Implement a `vectorbt` sweep module with parameter grids and top-N candidate selection.
- Define a strategy spec that can describe one strategy idea and generate both vectorbt signals and a backtrader strategy.
- Normalize result metrics across both engines.
- Document licensing and distribution implications before commercial packaging.
