# FastAPI Read-Only Backend

**Date:** 2026-05-10
**Spec:** [docs/superpowers/specs/2026-05-10-fastapi-readonly-backend-design.md](../superpowers/specs/2026-05-10-fastapi-readonly-backend-design.md)
**Plan:** [docs/superpowers/plans/2026-05-10-fastapi-readonly-backend.md](../superpowers/plans/2026-05-10-fastapi-readonly-backend.md)
**ADR:** [docs/adr/0009-fastapi-readonly-backend.md](../adr/0009-fastapi-readonly-backend.md)

## Summary

Added a read-only HTTP layer over the existing `quant_backtest` modules and
introduced a stable on-disk format for backtest report artifacts. The API
surfaces three resource groups — data (symbols, K-line, coverage), selection
(job-based with SSE progress), and reports (CLI-produced sweep + validate
runs). Long-running backtests stay in the CLI; the API only reads finished
reports.

## Why

CLI-only is the wrong UI for browsing daily-bar panels and sweep result tables.
The web frontend planned next needs a structured JSON surface; subprocess-ing
CLI commands would couple HTTP to text formatting and leak argparse semantics
into route handlers.

## What changed

### New modules

- `quant_backtest/services/` — shared business logic. `data_service` (symbol
  search, K-line + indicators, coverage), `selection_service` (run_selection
  with `on_progress` callback and result cache), `reports_service` (thin
  wrapper around `reports.store`).
- `quant_backtest/reports/` — `schema.py` defines `ReportManifest` /
  `SweepManifest` / `ValidateManifest`; `store.py` implements `write_report`,
  `list_reports`, `load_report`, `load_artifact`. Reports live under
  `reports/sweeps/{run_id}/` and `reports/validations/{run_id}/` with a
  `manifest.json`, `config.json`, and parquet artifacts. `run_id` is
  `{kind}-{yyyyMMdd-HHmmss}-{shortHash}` so identical config under different
  timestamps can be recognized by the trailing 6-char hash.
- `quant_backtest/api/` — FastAPI app with `create_app()` factory, RFC 7807
  error envelope, dependency injection for cache + reports dir, in-process
  `JobRegistry` (TTL 1h, no persistence), and routers under
  `routers/{system,data,reports,selection}.py`.

### CLI

- `quant-backtest sweep` and `quant-backtest validate` now write reports by
  default to `reports/`. Opt-out with `--no-report`. Override the base
  directory with `--reports-dir`.

### Dependencies

- `pyproject.toml` gained an `api` optional extra:
  `fastapi`, `uvicorn[standard]`, `pydantic>=2.9`, `sse-starlette`, `httpx`.
- New `quant-api` console script → `quant_backtest.api.app:run`.

### Test surface

Added 23 tests across 5 new files (`test_services_data`,
`test_services_selection`, `test_reports_store`, `test_api_health`,
`test_api_data`, `test_api_reports`, `test_api_selection`). The existing
`test_cli.py` was extended with `--no-report` / report-on-disk assertions.

## Decisions worth recording

- **Background work uses `threading.Thread`, not `asyncio.create_task`.** The
  initial implementation used `asyncio.create_task` inside the async submit
  handler. With `TestClient` (and any sync client), each request runs in its
  own ephemeral event loop and the task is cancelled when the loop exits. A
  daemon thread runs across request boundaries with no extra plumbing.
- **No selection timeout in v1.** The plan called for a 30s soft timeout on
  the background job. Cooperatively interrupting a numpy/pandas computation
  mid-flight is not clean to do in Python; the surface area for "hang
  forever" is low (single user, single process), so v1 ships without it.
  The README directs users to the CLI for long sweeps.
- **`cache.inspect()` returns one aggregate, not per-symbol.** Plan assumed
  per-symbol; `cache_coverage` was implemented to iterate `read_symbol` per
  cached symbol instead.
- **`.gitignore` `reports/` rule was anchored to `/reports/`.** Otherwise it
  would have shadow-blocked the new `src/quant_backtest/reports/` Python
  module.
- **`select_candidates` already takes `(date=, top_n=, latest=)` and embeds
  `min_score` / `require_factors` / `exclude_factors` into the
  `selected` column on the factor table.** The service calls
  `select_candidates(factor_table, date=as_of_ts, top_n=config.top_n)` and
  returns a slimmed `{symbol, score, factors_hit, reasons}` shape — distinct
  from the rich JSON the CLI prints. CLI output remains unchanged.

## Verification

- `uv run pytest` — 101 passed, 4 skipped (was 59 before this work, +42 tests
  added with no regressions).
- Manual smoke: `uv run quant-api` boots cleanly; `/docs` renders OpenAPI for
  all four routers.

## Follow-ups (not in scope)

- Persisting jobs to SQLite so progress survives a restart.
- Adding the second-tier reports (`hit-rate`, `validation-gap`) to the
  same artifact format.
- Cooperative cancellation / wall-clock timeout for selection.
