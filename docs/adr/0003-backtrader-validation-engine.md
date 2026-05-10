# ADR 0003: Backtrader Validation Engine

## Status

Accepted

## Context

The project needs a backtrader validation module that can use adjusted prices for signals while preserving raw prices for execution. This is important for A-share historical research because adjusted price series are useful for indicators but are not actual historical tradable prices.

## Decision

Implement a dedicated backtrader validation engine with:

- `BacktraderConfig`
- `BacktraderResult`
- `BacktraderEngine`
- custom A-share pandas feed
- analyzers for equity, orders, and trades
- built-in signal SMA cross example strategy

Default data semantics:

```text
signal_adjust = qfq
execution_adjust = raw
execution_timing = next_open
```

The feed exposes:

- raw execution lines: `open`, `high`, `low`, `close`, `volume`
- signal lines: `signal_open`, `signal_high`, `signal_low`, `signal_close`, `signal_volume`

## Reasoning

Using qfq prices as execution prices would create fills at prices that were not actually tradable on the historical date.

Using raw prices for indicators would create discontinuities around dividends, splits, and other corporate actions.

The feed therefore carries both price views. Strategies can compute features on `signal_close` and submit orders against the broker using raw execution OHLC.

`next_open` is the default execution timing because it avoids the common mistake of computing a signal with the current close and filling at the same close. `same_close` remains available for strategies that can legitimately generate signals before the close.

## Consequences

Positive:

- Backtrader validation has realistic execution-price semantics from the beginning.
- Strategy code can explicitly choose signal fields.
- Results are normalized into metrics and frames.
- Future paper trading work can preserve the signal/execution separation.

Tradeoffs:

- Feeds are project-specific rather than plain `bt.feeds.PandasData`.
- Strategy authors must know to use `signal_*` fields for adjusted signals.
- Current analyzers are intentionally simple and may need enrichment.

## Follow-Up Work

- Add result export to disk.
- Add position snapshots and daily holdings.
- Add A-share lot-size handling.
- Add limit-up and limit-down execution constraints.
- Add suspension behavior beyond warning-level data checks.
- Add benchmark comparison and excess return metrics.
- Add support for multi-strategy parameter validation.
