# Muce 牧策 — Documentation

A-share multi-factor quantitative research and backtesting toolkit documentation.

## How To Use These Docs

- `devlog/records/`: architecture decision records (ADR). Durable decisions about interfaces, data shape, dependencies, execution semantics, and future extensibility.
- `devlog/current/`: active cycle state — task backlog, system capabilities, current version PRD, and top-level overview.
- `devlog/appendix/`: stable reference docs — usage guides, templates, model contracts.
- `devlog/archive/`: frozen version snapshots (for version closeout).
- `devlog/CHANGELOG.md`: release-facing change summary.
- `superpowers/`: design-stage documents — brainstorm ideas, formal specs, and implementation plans.

## Current Documentation

### Records (all accepted)

- [ADR-001: A-share Data Layer](devlog/records/ADR-001_2026-05-07_a-share-data-layer.md)
- [ADR-002: Dual Backtesting Backends](devlog/records/ADR-002_2026-05-07_dual-backtesting-backends.md)
- [ADR-003: Backtrader Validation Engine](devlog/records/ADR-003_2026-05-07_backtrader-validation-engine.md)
- [ADR-004: VectorBT Research Engine](devlog/records/ADR-004_2026-05-07_vectorbt-research-engine.md)
- [ADR-005: Technical Indicator Layer](devlog/records/ADR-005_2026-05-08_technical-indicator-layer.md)
- [ADR-006: Daily Stock Selector](devlog/records/ADR-006_2026-05-08_daily-stock-selector.md)
- [ADR-007: Full-Market Storage And Query Layer](devlog/records/ADR-007_2026-05-08_full-market-storage-and-query-layer.md)
- [ADR-008: Selector Hit-Rate Validation](devlog/records/ADR-008_2026-05-09_selector-hit-rate-validation.md)
- [ADR-009: FastAPI Read-Only Backend](devlog/records/ADR-009_2026-05-10_fastapi-readonly-backend.md)
- [ADR-010: Three-Falling Buy Strategy](devlog/records/ADR-010_2026-05-07_three-falling-buy-strategy.md)
- [Records Index](devlog/records/README.md)

### Current State

- [Overview](devlog/current/overview.md) — top-level project state
- [Capabilities](devlog/current/capabilities.md) — what the system can do
- [Task Backlog](devlog/current/task-backlog.md) — unresolved issues and future directions
- [PRD](devlog/current/prd.md) — maturity gap roadmap (P0-P3 requirements)

### Appendices

- [Backtrader Validation Guide](devlog/appendix/backtrader-validation.md)
- [Documentation Process](devlog/appendix/documentation-process.md)
- [ADR Template](devlog/appendix/templates/adr-template.md)

### Design

- [Brainstorm: Trading Method Modules](superpowers/brainstorm/trading-method-modules.md)
- [Spec: FastAPI Read-Only Backend](superpowers/specs/2026-05-10-fastapi-readonly-backend-design.md)
- [Plan: FastAPI Read-Only Backend](superpowers/plans/2026-05-10-fastapi-readonly-backend.md)

### Change Log

- [CHANGELOG](devlog/CHANGELOG.md)

## Documentation Rule

When a development session changes behavior, architecture, dependencies, assumptions, or future direction, update at least one document in `docs/devlog/`. Small bug fixes can be recorded in a `records/` review entry; durable decisions should get a decision ADR. Current state updates go in `devlog/current/`.
