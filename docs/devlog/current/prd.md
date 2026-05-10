# Quant System Maturity Gap Roadmap (PRD)

## Status

Active requirements document.

This document compares the current project with mature quant trading platforms such as PTrade and portfolio/trade management terminals. It defines the functional gaps, priority order, and delivery standards for future development.

Mature platforms are broader systems. PTrade-style platforms combine research, backtesting, simulation, live trading, scheduling, data access, order events, transaction events, risk control, and broker-side execution. Portfolio/trade management terminals additionally emphasize portfolio accounting, multi-strategy operation, OMS/PMS workflows, monitoring, audit, and reporting.

Therefore, the next phase should not focus only on adding more trading ideas. The project needs a stronger engineering foundation so that strategy results are reproducible, explainable, testable, and eventually executable.

## Engineering Principles

Every item below must be implemented according to these rules:

- Define the behavioral contract before coding.
- Keep modules single-purpose and composable.
- Prefer explicit domain objects over loose dictionaries once behavior spans multiple modules.
- Make data semantics visible: source, adjustment, calendar, frequency, execution timing, and assumptions must be explicit.
- Add focused tests before or alongside implementation.
- Preserve existing behavior unless the requirement explicitly changes it.
- Make outputs reproducible: same inputs and config should produce the same result.
- Add logging, diagnostics, or exportable artifacts when behavior is hard to inspect.
- Document the decision and remaining risks after implementation.
- Avoid optimizing for one backtest result; prefer robustness, explainability, and validation across engines.

## Delivery Checklist

Each requirement should be closed only when it has:

- A clear problem statement.
- A proposed interface or command.
- Unit tests for core logic.
- Integration or smoke tests when data/backtest workflows are affected.
- Documentation update in devlog, ADR, backlog, or guide.
- A verification command recorded in the final implementation note.
- Known limitations listed explicitly.

## Priority Order

Priority definitions:

- `P0`: blocks trustworthy strategy research.
- `P1`: required before serious multi-year or full-market strategy evaluation.
- `P2`: required before paper trading or live trading.
- `P3`: improves workflow, usability, or extensibility after the core is stable.

## P0 Requirements

### P0-1: Diagnose Simulator Versus Backtrader Differences

Status: ✅ Done.

- Diagnostic tool implemented and iterated through six revisions.
- First full-market report at `reports/validation-gap/selector-rsi70-boll15-next-open/` and latest at `...-v6/`.
- Findings recorded in `docs/devlog/2026-05-09-validation-gap-diagnostics.md`.
- Backtrader validation now preserves selector candidate order, uses lot-size sizing, records `entry_bar` on completed fills, exits via explicit close orders, and no longer rejects next-open entries when the signal-day close is limit-up.

Problem:

- The fast execution simulator and Backtrader validation produced materially different results for the same layered selector candidate (initially 36 percentage points; reduced to about 28 percentage points after the v6 fixes).
- This made simulator sweep results useful for search, but not yet trustworthy enough for final strategy selection.

Why it matters:

- If two engines disagree, we do not know whether the edge is real or caused by order timing, sizing, valuation, or fill semantics.

Acceptance criteria:

- Reports simulator orders, Backtrader orders, fills, cash, positions, and equity curve side by side.
- Identifies first divergence date.
- Separates differences by category: sizing, entry date, exit date, fill price, commission, slippage, rejected order, valuation.
- Includes tests with a tiny deterministic dataset where both engines should match.

Current finding:

- First divergence now occurs at the first fill date with category `sizing` only, not symbol-selection or odd-lot.
- Remaining gap is expected: the simulator sizes with the known next-open fill price, while Backtrader sizes from information available at signal-day close. This is the trigger for P0-2.

### P0-2: Realistic Next-Open Sizing In Simulator

Problem:

- The simulator currently sizes positions using the next-open fill price, which is information not available at the signal-day close.

Why it matters:

- This is the root cause of the remaining simulator-vs-Backtrader gap. Until it is fixed, simulator sweep results stay optimistic compared to a realistic execution path.

Proposed capability:

- Add a sizing-mode option to `SelectionExecutionConfig`:

```text
next_open_sizing_mode = "future_open" | "estimated_close"
```

- Default new runs to `estimated_close`. Keep `future_open` available only for archived comparison artifacts and clearly tagged as optimistic.
- Re-run `diagnose-validation-gap` after the change. Require remaining gaps to either disappear or be explainable as P0-3 (rejection logging) or P0-5 (market rules) effects.

Acceptance criteria:

- Same selector candidate produces simulator sizing and Backtrader sizing within an acceptable, deterministic tolerance under `estimated_close` mode.
- Existing tests still pass.
- Devlog records the new gap distribution after the fix.

### P0-3: Strategy-Level Skipped-Candidate Logging

Problem:

- The current Backtrader validation does not separately record strategy-level skipped candidates from broker rejections.
- The diagnostic tool builds an ad-hoc category list per run.

Why it matters:

- Without canonical rejection categories, every new sweep produces non-comparable diagnostic output. It also blocks the future risk-control layer (P2-3), which must report its own reasons in the same vocabulary.

Proposed capability:

- Define a single canonical rejection category set used by simulator and Backtrader:

```text
strategy_skipped
limit_up_buy_blocked
limit_down_sell_blocked
insufficient_cash
lot_rounding
broker_reject
risk_rule_<name>
other
```

- Replace the simulator's existing rejection labels and Backtrader's strategy-level skips with this shared schema.
- Update `diagnose-validation-gap` to consume this schema instead of producing its own.

Acceptance criteria:

- Both engines emit Order objects with the same `rejection_reason` enum.
- Diagnostic report counts rejections per category.
- Tests cover at least limit-up buy, limit-down sell, insufficient cash, and lot rounding.

### P0-4: Unified Portfolio, Broker, Order, And Fill Model

Status: **Active** — blocking item, should land before P0-2/P0-3/P0-5.

Problem:

- Current logic is split across selector simulation, Backtrader adapters, and metric utilities.
- Portfolio state and order semantics are not yet represented as stable domain objects.

Why it matters:

- Without a shared model, every strategy and engine can interpret cash, positions, orders, and fills differently.
- P0-2 (sizing modes), P0-3 (rejection categories), P0-5 (market rules), and P2-2/P2-3 (paper trading + risk layer) all need a single canonical representation.

Proposed capability:

- Define core domain objects in `src/quant_backtest/exec/model.py`:

```text
Portfolio
Position
Order
Fill
BrokerState
ExecutionReport
```

- `Order` lifecycle: `submitted -> accepted | rejected(reason) -> partially_filled -> filled | canceled`.
- Reserve `risk_check(order, portfolio, market) -> Allow | Reject(reason)` hook so P2-3 can plug in without re-shaping the model.
- Use these objects in the custom simulator. Provide a thin adapter from Backtrader outputs into the same schema.

Acceptance criteria:

- Same trade sequence produces identical cash, position, and equity state in unit tests for both adapters.
- Orders and fills can be exported to Parquet/CSV with stable column names.
- Backtrader validation output can be normalized into the same order/fill schema.
- The `risk_check` hook exists and is exercised by at least one test, even if the default policy is allow-all.

### P0-5: A-Share Market Rules Engine

Status: depends on P0-4.

Problem:

- A-share-specific execution rules are only partially modeled and scattered across config flags.

Why it matters:

- A daily selector can look profitable if it ignores T+1, board-specific price limits, lot size, suspensions, and execution infeasibility near limit-up/limit-down.

Proposed capability:

- Add a configurable `MarketRules` plug-in to the unified broker:

```text
lot size (with board-specific exceptions)
T+1 sell availability
ST and non-ST price limits
main board / STAR / ChiNext / Beijing limit rules
suspension handling
IPO / new-stock first-day rules
limit-up buy rejection
limit-down sell rejection
minimum price tick
commission, stamp tax, transfer fee
volume participation cap
partial fill policy
```

Acceptance criteria:

- Rules are explicit in strategy/backtest config and recorded in run `meta.json`.
- Unit tests cover normal stocks, ST stocks, 10%/20% price-limit boards, suspension, and T+1.
- Backtest reports summarize blocked buys, blocked sells, partial fills, and rejected orders, using the canonical category set from P0-3.

### P0-6: Feature And Factor Cache

Status: can run in parallel with P0-2 / P0-3 / P0-5 because it is structurally independent.

Problem:

- Current full-market layered sweeps repeatedly recompute indicators and factor tables.
- This is already slow for RSI/Bollinger sweeps and will become impractical for KDJ/MACD window grids.

Why it matters:

- Slow research loops encourage smaller, biased tests and make systematic validation harder.

Proposed capability:

- Persist feature and factor tables with versioned metadata.

Suggested layout:

```text
data/features/a_share/daily/
  feature_set=technical_v1/
    source=baostock/
      adjust=qfq/
        symbol=000001.SZ/part.parquet

data/factors/a_share/daily/
  factor_set=selector_v1/
    selector_hash=.../
      part.parquet
```

Acceptance criteria:

- Feature metadata records source, adjust, frequency, calendar, formula version, and indicator config.
- Re-running a sweep can reuse compatible cached features.
- Incompatible metadata fails loudly instead of silently mixing feature definitions.
- CLI can build and inspect feature coverage.

## P1 Requirements

### P1-1: Multi-Year Full-Market Data Expansion

Status: can start any time. The work is mostly an overnight download, not coding.

Problem:

- Current full-market selector tests use about one year of daily data.

Why it matters:

- One year is not enough to evaluate regime dependence, overfitting, or robustness.

Proposed capability:

- Extend A-share full-market daily cache to at least three years, preferably five.
- Store universe membership, listing date, delisting status, ST status, and suspension status by date where possible.
- Add resume/retry logging around failed symbols.

Acceptance criteria:

- Cache health report includes symbol count, row count, date range, missing rows, duplicates, ST rows, suspended rows, and last update time.
- Selector backtests can be run over rolling train/test windows.

### P1-2: Factor Evaluation Module

Problem:

- Current selector evaluation focuses on hit rate and portfolio backtest results.
- It does not yet provide a rigorous factor research view.

Why it matters:

- A factor should be evaluated by predictive power, monotonicity, turnover, decay, stability, and exposure, not only by one strategy curve.

Proposed capability:

- Add factor analytics:

```text
IC
RankIC
quantile returns
long-short spread
factor decay
turnover
coverage
industry exposure
market-cap exposure
correlation with existing factors
```

Acceptance criteria:

- Factor reports can be generated for one factor and for a factor set.
- Reports can be exported to local files.
- Tests verify formulas on deterministic toy data.

### P1-3: Walk-Forward And Out-Of-Sample Validation

Problem:

- Current sweep results are in-sample.

Why it matters:

- Parameter sweeps can overfit easily, especially with many technical thresholds.

Proposed capability:

- Add walk-forward evaluation:

```text
train window
validation window
test window
rolling or expanding mode
parameter selection rule
out-of-sample report
```

Acceptance criteria:

- The selected parameter set must be chosen only from training/validation data.
- Test-period results are reported separately.
- Report compares in-sample versus out-of-sample degradation.

### P1-4: Result Export And Research Artifact Management

Status: 🟡 partial — `diagnose-validation-gap` already writes structured artifacts.

Problem:

- Most CLI commands still print JSON to stdout. Artifacts are not consistently archived.

Why it matters:

- Serious research needs durable artifacts for comparison, replay, and review.

Proposed capability:

- Adopt one canonical layout used by every CLI: backtests, sweeps, validation, hit-rate, simulate, walkforward, diagnose:

```text
reports/<command>/<run_id>/
  meta.json         # run id, kind, status, created_at, finished_at
  config.json       # full submitted config (incl. market rules, risk settings)
  metrics.json      # headline metrics
  equity.parquet
  orders.parquet
  trades.parquet
  positions.parquet
  candidates.parquet
  summary.md        # short human-readable summary
```

Acceptance criteria:

- Every CLI accepts `--out` and `--run-id` consistently.
- Artifact layout matches what a future Dashboard (P3-2) can consume directly.
- Runs are timestamped, reproducible, and can be re-loaded for comparison.

## P2 Requirements

### P2-1: Minute Data And Tail-Close Execution Validation

Problem:

- Current strategies often assume close-time or next-open execution using daily bars.

Why it matters:

- Tail-close stock selection cannot be validated with daily data alone. It needs minute or tick data to model whether orders could be filled near the intended price.

Proposed capability:

- Add minute-level data provider/cache for selected symbols or selected candidate dates.
- Validate close-time selection using minute bars around the final trading window.

Acceptance criteria:

- Can load minute data for candidate symbols and dates.
- Reports tail-window liquidity, price movement, limit status, and estimated fill quality.
- Clearly separates daily-bar approximation from minute-validated execution.

### P2-2: Paper Trading Architecture

Status: depends on P0-4 unified model.

Problem:

- The project has no live or paper trading loop.

Why it matters:

- Moving from research to execution requires scheduling, data refresh, signal generation, order proposal, risk checks, and broker submission.

Proposed capability:

```text
daily data update
feature build
signal generation
portfolio check
risk check (P2-3)
order proposal
manual approval or paper execution
execution report
post-trade reconciliation
```

Acceptance criteria:

- Paper trading can run without broker credentials.
- Generated orders are auditable before execution.
- Risk checks can reject orders before they reach any broker adapter.
- Daily snapshots are persisted for replay and reconciliation.

### P2-3: Risk Control Layer

Status: hook reserved by P0-4.

Problem:

- Current risk controls are embedded in backtest configs and not yet a separate layer.

Why it matters:

- Mature systems need centralized risk controls independent of strategy code, used identically in backtest, paper, and live.

Proposed capability:

```text
max single-name weight
max industry weight
max daily turnover
max drawdown stop
max order value
min liquidity
blacklist / whitelist
limit-up and limit-down checks
cash buffer
```

Acceptance criteria:

- Risk rules run before simulated or paper orders.
- Rejected orders include machine-readable reasons that match the P0-3 canonical category set.
- Backtests can report what would have been blocked by each risk rule.

## P3 Requirements

### P3-1: Unified Pipeline Command

Problem:

- Current workflow requires several separate commands.

Proposed capability:

```bash
quant-pipeline run \
  --data update \
  --features build \
  --selector sweep \
  --validate backtrader \
  --report
```

Acceptance criteria:

- Pipeline writes a complete run artifact directory matching the P1-4 layout.
- Each stage is still independently callable.
- Stages are skippable and resumable.

### P3-2: Research Dashboard Or Report UI

Status: 🧊 deferred. Replaces the earlier standalone frontend plan.

Problem:

- JSON output is not enough for quick research comparison.

Why it matters:

- Once the engineering core is trustworthy, a visual surface accelerates research without expanding scope back into product territory.

Proposed capability:

- Generate static or web-served reports for:

```text
equity curve
drawdown
monthly returns
parameter heatmaps
trade distribution
factor attribution
engine comparison (simulator vs Backtrader)
```

Implementation candidates, in increasing scope:

- Static HTML viewer that reads canonical artifact directories from P1-4.
- Streamlit or Gradio app (Python-only).
- Vite + React + Tailwind + shadcn/ui front-end backed by a thin FastAPI layer.

Acceptance criteria:

- Report can be opened locally without launching paid services.
- The Dashboard does not become a dependency of the core data/backtest layer.
- The earlier 14-item Vite+React+FastAPI plan is preserved as a possible expansion path, but is not required for P3-2 to ship.

### P3-3: Optional MCP Server Wrapper

Status: 🧊 deferred. Recorded so it is not lost.

Problem:

- Driving research and backtests from Claude Code / Cursor / Codex currently requires shell calls.

Proposed capability:

- Wrap `quant-data`, `quant-backtest`, and `quant-select` in a thin MCP server. No new logic, only an alternate transport.
- Inspired by reference projects in the same domain that publish MCP servers as a separate package.

Acceptance criteria:

- MCP server is in a separate optional extras (`mcp`) group.
- Tests run in CI without requiring the MCP server.

## Working Sequence

The recommended implementation sequence is:

1. ✅ P0-1: diagnose simulator versus Backtrader differences. *Done v6.*
2. P0-4: introduce unified Portfolio/Broker/Order/Fill model. *(Foundation for next items.)*
3. P0-5: implement A-share market rules engine.
4. P0-2: add realistic next-open sizing to the simulator.
5. P0-3: add strategy-level skipped-candidate logging.
6. P0-6: persist features and factor tables. *(Can start in parallel with P0-2/3/5.)*
7. P1-1: expand to multi-year full-market data. *(Can start in parallel — overnight download, not coding work.)*
8. P1-2: add factor evaluation module.
9. P1-3: add walk-forward validation.
10. P1-4: export durable research artifacts under canonical layout.
11. P2-1: add minute-data validation for tail-close execution.
12. P2-2 and P2-3: build paper trading and risk layers.
13. P3 items: improve workflow, dashboard, and MCP wrapper after the core is stable.

P0-4 is sequenced before P0-2/P0-3/P0-5 because those three either define rejection categories, sizing modes, or rule semantics that must live on the unified Order/Portfolio/Broker schema. Doing them first would force a rewrite later.

## Current Next Task

`P0-4: Unified Portfolio, Broker, Order, And Fill Model`.

Reason:

- P0-1 is complete enough to act on; the remaining sizing gap is explained.
- P0-2, P0-3, and P0-5 all need a stable Order/Portfolio/Broker schema. Doing them first will force a rewrite.
- P0-6 is independent and can run in parallel with P0-4 if a second track is opened.

## Licensing And Distribution

Status: ✅ baseline in place.

- Project license: `GPL-3.0-or-later` (chosen because of `backtrader` copyleft propagation).
- `LICENSE` file at repository root contains the official GPL-3.0 text.
- `pyproject.toml` declares license metadata via PEP 639 (`license = "GPL-3.0-or-later"`, `license-files = ["LICENSE"]`).
- `README.md` documents permitted use and the constraints from `vectorbt` (free tier) Commons Clause.

Permitted today:

- Personal research, self-directed live trading, academic work.
- Free open-source distribution under GPL-3.0.
- Internal use within an organization that does not redistribute or sell access.

Blocked today (would require rework before being allowed):

- Selling the project as a paid product, hosted SaaS, or fee-based consulting offering while it depends on `vectorbt` (free tier). The Commons Clause forbids this.
- Releasing a closed-source binary or commercial fork while it depends on `backtrader`. GPL-3.0 forbids this.

If commercial use ever becomes a goal:

- Replace `vectorbt` (free tier) with `vectorbt PRO` (commercial), `bt`, `zipline-reloaded`, or a custom vectorized engine.
- Either keep the project GPL-compatible or replace `backtrader` (e.g. with `bt` MIT or `zipline-reloaded` Apache-2.0).
- This decision must not be made silently. It is recorded here so it remains visible.