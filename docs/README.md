# Quant Project Documentation

This directory records design thinking, implementation decisions, development history, and future work for the A-share quant research and backtesting project.

## How To Use These Docs

- `devlog/`: chronological engineering notes. Use this to capture what changed, why it changed, verification results, and open questions after each development session.
- `adr/`: architecture decision records. Use this when a decision affects interfaces, data shape, dependencies, storage, execution semantics, or future extensibility.
- `requirements/`: prioritized requirements and maturity gap roadmaps. Use this to define what must be built next and how completion will be judged.
- `brainstorm/`: structured idea maps and module candidates before they become implementation requirements.
- `backlog/`: unresolved issues, future requirements, and possible solution directions.
- `guides/`: stable reference docs for how the current system works and how to use it.

## Current Docs

- [Project Origin And First Implementation](devlog/2026-05-07-project-origin-and-v1-implementation.md)
- [Three-Rising Factor MVP](devlog/2026-05-07-three-rising-factor-mvp.md)
- [Three-Falling Buy And Three-Rising Sell](devlog/2026-05-07-three-falling-buy-three-rising-sell.md)
- [VectorBT Research Engine](devlog/2026-05-07-vectorbt-research-engine.md)
- [Technical Indicator Layer](devlog/2026-05-08-technical-indicator-layer.md)
- [Daily Stock Selector](devlog/2026-05-08-daily-stock-selector.md)
- [Full-Market Data Preparation](devlog/2026-05-08-full-market-data-prep.md)
- [Validation Gap Diagnostics](devlog/2026-05-09-validation-gap-diagnostics.md)
- [FastAPI Read-Only Backend](devlog/2026-05-10-fastapi-readonly-backend.md)
- [ADR 0001: A-share Data Layer](adr/0001-a-share-data-layer.md)
- [ADR 0002: Dual Backtesting Backends](adr/0002-dual-backtesting-backends.md)
- [ADR 0003: Backtrader Validation Engine](adr/0003-backtrader-validation-engine.md)
- [ADR 0004: VectorBT Research Engine](adr/0004-vectorbt-research-engine.md)
- [ADR 0005: Technical Indicator Layer](adr/0005-technical-indicator-layer.md)
- [ADR 0006: Daily Stock Selector](adr/0006-daily-stock-selector.md)
- [ADR 0007: Full-Market Storage And Query Layer](adr/0007-full-market-storage-and-query-layer.md)
- [ADR 0008: Selector Hit-Rate Validation](adr/0008-selector-hit-rate-validation.md)
- [ADR 0009: FastAPI Read-Only Backend](adr/0009-fastapi-readonly-backend.md)
- [Quant System Maturity Gap Roadmap](requirements/maturity-gap-roadmap.md)
- [Brainstorm: Trading Method Modules](brainstorm/trading-method-modules.md)
- [Current Backlog](backlog/current.md)
- [Backtrader Validation Guide](guides/backtrader-validation.md)
- [Documentation Process](guides/documentation-process.md)

## Documentation Rule

When a development session changes behavior, architecture, dependencies, assumptions, or future direction, update at least one document in this directory. Small bug fixes can be recorded in `devlog/`; durable decisions should also get an ADR.
