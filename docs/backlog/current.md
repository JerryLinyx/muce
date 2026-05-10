# Current Backlog

This backlog records known problems, future requirements, and possible solution directions. Items here are not commitments; they are preserved so design context is not lost.

## Priority Roadmap

The active maturity-gap requirements are maintained in:

- [Quant System Maturity Gap Roadmap](../requirements/maturity-gap-roadmap.md)
- [Brainstorm: Trading Method Modules](../brainstorm/trading-method-modules.md)

Current priority order (synced with `requirements/maturity-gap-roadmap.md`):

P0 — Backtest trustworthiness:

1. P0-1 Diagnose simulator versus Backtrader differences. ✅ v6 landed; remaining gap is sizing.
2. P0-2 Add realistic next-open sizing to the simulator so it sizes from signal-day close, not the future open.
3. P0-3 Add strategy-level skipped-candidate logging with a canonical rejection category set.
4. P0-4 Introduce a unified Portfolio / Broker / Order / Fill model. **Blocking — sequence first.**
5. P0-5 Implement an A-share market rules engine on top of the unified model.
6. P0-6 Persist feature and factor tables for faster full-market sweeps. *(Can run in parallel.)*

P1 — Serious research:

7. P1-1 Expand full-market data to multi-year coverage. *(Can start any time — overnight download.)*
8. P1-2 Add factor evaluation: IC, RankIC, quantile returns, decay, turnover, exposure.
9. P1-3 Add walk-forward and out-of-sample validation.
10. P1-4 Adopt canonical run artifact layout under `reports/<command>/<run_id>/`.

P2 — Closer to real trading:

11. P2-1 Add minute-data validation for tail-close execution.
12. P2-2 Build paper trading architecture.
13. P2-3 Add a centralized risk-control layer (hook reserved by P0-4).

P3 — Experience and extension:

14. P3-1 Add a unified `quant-pipeline` command.
15. P3-2 Research Dashboard / report UI. *(Replaces the earlier standalone Vite+React+FastAPI frontend plan, which is preserved as one of three implementation candidates.)*
16. P3-3 Optional MCP server wrapper around the existing CLI.

Recommended execution order across P0:

```
P0-4 (foundation) → P0-5 → P0-2 → P0-3 → P0-6 (parallel)
```

P0-4 ships before the other P0 items because they all need a stable Order / Portfolio / Broker schema.

## Data Layer

### Real Baostock Download Smoke Test

Need:

- Verify real `baostock` downloads for several A-share symbols.
- Confirm field mapping and date parsing with live data.
- Confirm `qfq`, `raw`, and `hfq` cache partitions are populated correctly.

Possible direction:

- Add pytest integration marker: `@pytest.mark.integration`.
- Keep network tests off by default.
- Use a short historical range and 1-2 stable symbols.

### DuckDB Query Layer

Status:

- Optional `DuckDBReader` has been added.

Need:

- Query cached Parquet partitions for cross-sectional research.
- Avoid duplicating data into another primary store too early.

Possible direction:

- Implement `DuckDBReader` over existing Parquet files.
- Provide queries like symbol/date filters, date range panels, and data health summaries.
- Keep Parquet as the source of truth in v1.

### Trading Calendar

Need:

- Detect missing trading days more accurately than simple date gap heuristics.

Possible direction:

- Add a CN SSE/SZSE calendar provider.
- Store calendar version in metadata.
- Validate symbol rows against expected trading sessions.

### Corporate Actions And Dual Price Mode

Need:

- Preserve exact semantics for qfq signal prices and raw execution prices.
- Avoid accidental mixed adjustment modes.

Possible direction:

- Add explicit `PriceView` or `DataBundle` objects.
- Make strategy configuration declare whether it consumes qfq, hfq, or raw signals.

## Backtrader Validation

### Three-Rising Factor Robustness

Need:

- Treat the three-consecutive-bullish-days strategy as an MVP, not a validated edge.
- Compare same-close execution against less optimistic execution timings.
- Check whether the sample size over one stock and one year is too small.

Possible direction:

- Run the same factor on `603986.SH` over 3-5 years.
- Run a next-open entry/exit variant.
- Sweep `hold_bars` from 1 to 5.
- Run across a semiconductor stock basket instead of one stock.

### Three-Falling Buy / Three-Rising Sell Robustness

Need:

- Validate whether the strong one-year `603986.SH` result is robust or just sample-specific.
- Understand whether most profit comes from one large trend trade.
- Compare same-close execution against next-open execution.

Possible direction:

- Run `same_close` vs `next_open`.
- Run slippage at 5, 10, 20, and 50 bps.
- Run over 3-5 years.
- Run across a basket of semiconductor and large-cap A-share names.
- Add per-trade contribution analysis.

### Result Export

Need:

- Export `metrics`, `equity_curve`, `orders`, and `trades` to CSV or Parquet.

Possible direction:

- Add `BacktraderResult.export(path, format="parquet")`.
- Add CLI `--out`.

### Position Snapshots

Need:

- Record daily holdings and market value per symbol.

Possible direction:

- Add a `PositionAnalyzer`.
- Include size, price, market value, cost basis if available, and portfolio weight.

### A-share Execution Rules

Need:

- Model lot size, suspension, ST constraints, limit-up/limit-down, and possibly T+1 behavior.

Possible direction:

- Start with lot-size rounding.
- Add a simple limit-up/down rejection model after raw high/low and previous close semantics are confirmed.
- Make each market rule configurable.

### Strategy Interface

Need:

- Move beyond the built-in SMA example.
- Allow strategy ideas to be packaged and run consistently.

Possible direction:

- Define a `StrategySpec` with parameters, default values, and backtrader/vectorbt builders.
- Keep framework-specific strategy classes behind adapter methods.

## vectorbt Research

### Parameter Sweep Module

Status:

- Initial VectorBT sweep engine is implemented.

Need:

- Pass top candidates into Backtrader validation.
- Export sweep result tables.

Possible direction:

- Save candidate parameter sets to JSON or Parquet.
- Add `quant-pipeline sweep-then-validate`.

### Cross-Engine Metric Normalization

Need:

- Compare vectorbt sweep results with backtrader validation results.

Possible direction:

- Define common metric names: total return, annual return, max drawdown, Sharpe, trade count, turnover.
- Track engine-specific metrics separately.

## Feature Layer

### Persisted Feature Store

Need:

- Avoid recomputing common indicators repeatedly for large universes.
- Version feature definitions so formula or parameter changes do not silently mix outputs.

Possible direction:

- Add `data/features/a_share/daily/feature_set=technical_v1/symbol=.../part.parquet`.
- Store feature metadata such as `feature_set`, source adjust mode, formula version, and config.
- Keep raw OHLCV cache as the source of truth.

### Feature CLI

Need:

- Build and inspect indicator features from cached qfq/raw bars.

Possible direction:

- Add `quant-features build --symbols ... --adjust qfq --feature-set technical_v1`.
- Add `quant-features inspect` for row counts, feature coverage, NaN warmup counts, and metadata.

### External Indicator Library Comparison

Need:

- Understand formula differences between project-owned indicators, TA-Lib, pandas-ta, and VectorBT.

Possible direction:

- Add optional comparison tests behind extras.
- Start with MACD, RSI, KDJ, Bollinger Bands, and ATR.
- Treat warmup and smoothing differences as explicit semantics rather than hidden mismatches.

## Stock Selection

### Full-Market Universe Download

Status:

- One-year full-market qfq/raw daily cache has been downloaded for 5200 A-share symbols.

Need:

- Extend to three years before treating selector backtests as meaningful.
- Decide whether to persist feature tables before repeated full-market sweeps.

Possible direction:

- Use the existing Baostock universe provider for the first three-year cache.
- Add a feature-store layer before large parameter grids.

### Selector Hit-Rate And Factor Attribution

Status:

- `quant-select hit-rate` and `quant-select sweep-hit-rate` are implemented.
- First one-year full-market baseline with `min_score=4`, `top_n=10`, and next-close labels produced a 46.27% valid-signal win rate.
- `quant-select attribution` is implemented.
- Hard selector filters `require_factors` and `exclude_factors` are implemented.
- First strict candidate rule found: require KDJ golden cross, MACD golden cross, RSI momentum, and Bollinger breakout; exclude MA breakout and volume breakout.
- `quant-select simulate` is implemented for execution-aware selector tests with lot-size rounding, limit-up buy rejection, limit-down sell rejection, and surge slippage.
- `quant-select sweep-simulate` is implemented for execution-aware parameter sweeps.
- Current close-time sweep candidate: hold 5 days, top 5 candidates, max 1 position, 20% target allocation, 20% take-profit, no stop-loss.
- `quant-select validate-backtrader` is implemented for precomputed selector signal validation.
- Backtrader validation changed the current preferred candidate to hold 5 days, top 5 candidates, max 1 position, 20% target allocation, no take-profit, no stop-loss.
- `quant-select sweep-simulate` now supports layered factor-parameter lists for min score, RSI threshold, volume multiplier, and Bollinger standard deviation.
- Current layered strict-selector candidate is `rsi_threshold=70`, `boll_std=1.5`, `top_n=3`, `hold_days=10`, `target_percent=20%`, `max_positions=2`, no stop-loss/take-profit.
- Backtrader validation for that candidate is materially lower than the fast simulator: about 30% total return and Sharpe about 1.9 versus simulator next-open about 66.6% and Sharpe about 2.7.

Need:

- Understand which factor combinations create winners and losers.
- Avoid overfitting to one year of in-sample results.
- Add daily and monthly regime summaries.
- Validate the strict rule under more realistic execution assumptions.
- Validate the current Backtrader candidate with minute-level data or more conservative tail-close fill assumptions.
- Diagnose simulator-vs-Backtrader differences for the layered candidate before trusting larger sweeps.
- Improve sweep performance by caching factor tables or materializing indicator features; current Pandas full-market recomputation is too slow for KDJ/MACD window grids.

Possible direction:

- Add factor-combination attribution by `factor_reasons`.
- Sweep Bollinger semantics: above middle band, upper-band breakout, band-width expansion.
- Sweep KDJ/MACD definitions: golden cross only, above zero/above 50 filters, cross plus trend confirmation.
- Add walk-forward evaluation: train parameter choice on earlier windows, test on later windows.
- Use Backtrader only for the small set of selector configurations that survive hit-rate and vectorized portfolio tests.
- Add a `quant-select diagnose-validation-gap` style report comparing the same candidate orders between simulator and Backtrader.
- Consider persisting `factor_table` outputs by `{source, adjust, indicator_config, selector_config_hash}` to speed up repeated layered sweeps.
- Add constraints before any serious portfolio result: max 10-20% per stock, minimum amount, minimum price, no one-day limit-up entry, no one-day limit-down exit, and lot-size rounding.
- Add richer A-share market rules: exact board-specific limit rounding, IPO/new-stock limit rules, T+1 position availability, and partial-fill assumptions.
- Add minute-level data before claiming true tail-close executability.
- Store universe membership snapshots by date to avoid survivorship bias.

### Selector Robustness

Need:

- Avoid treating a simple additive factor score as a validated alpha model.
- Measure factor contribution, turnover, hit rate, and regime dependence.

Possible direction:

- Add per-factor performance attribution.
- Add factor weights and threshold sweeps.
- Add walk-forward validation and train/test date splits.

### Selector Execution Validation

Need:

- Validate top selector configurations with Backtrader and A-share market rules.

Possible direction:

- Convert daily candidates into Backtrader target orders.
- Add max positions, max single-name weight, rebalance timing, lot size, T+1, and limit-up/limit-down checks.

## CLI And Workflow

### End-To-End Command

Need:

- One command to download qfq/raw, inspect cache, run sweep, then validate candidates.

Possible direction:

- Add `quant-pipeline run`.
- Keep subcommands composable rather than hiding all steps.

### Documentation Updates

Need:

- Keep design context current as implementation changes.

Possible direction:

- Update `devlog/` after each substantial development session.
- Add ADRs for durable architectural choices.
- Move stable usage docs into `guides/`.

## Licensing And Distribution

Status: ✅ baseline in place.

- Project license: `GPL-3.0-or-later` (chosen because of `backtrader` copyleft propagation).
- `LICENSE` file at repository root contains the official GPL-3.0 text.
- `pyproject.toml` declares license metadata via PEP 639.
- `README.md` documents permitted use and the constraints from `vectorbt` (free tier) Commons Clause.

Permitted today: personal research, self-directed live trading, academic work, free open-source distribution under GPL-3.0, internal organizational use.

Blocked today: paid product / hosted SaaS / fee-based consulting offering while depending on `vectorbt` (free tier) — Commons Clause forbids it. Closed-source binary or commercial fork while depending on `backtrader` — GPL-3.0 forbids it.

If commercial use ever becomes a goal, replace `vectorbt` (free tier) with `vectorbt PRO` / `bt` / `zipline-reloaded` / custom engine, and either keep the project GPL-compatible or replace `backtrader`. This decision must not be made silently.

## Deferred — Earlier Frontend Plan

The earlier 14-item frontend plan (Vite + React + TS + Tailwind + shadcn/ui + FastAPI + filesystem RunStore) was scoped before the priority refresh. It is **not abandoned**. It is now deferred to P3-2 (Dashboard) as one of three candidate implementations:

1. Static HTML viewer over the canonical artifact layout from P1-4 (lightest).
2. Streamlit / Gradio (Python only).
3. Vite + React + Tailwind + shadcn/ui + FastAPI (the original plan, heaviest).

The plan will not be revisited until P0 is stable and P1-4 has fixed the artifact contract that any UI must read.
