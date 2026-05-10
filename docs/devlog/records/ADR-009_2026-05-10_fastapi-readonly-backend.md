---
id: ADR-009
kind: decision
title: FastAPI Read-Only Backend
date: 2026-05-10
status: accepted
---

# ADR 0009: FastAPI Read-Only Backend

## Status

Accepted (2026-05-10).

## Context

Muce was CLI-only. A web frontend was planned. We needed an HTTP layer that:

- Exposes data, selection, and backtest reports as JSON.
- Doesn't couple to CLI text output (which uses `print(json.dumps(...))` and
  bakes argparse into business logic).
- Doesn't introduce infrastructure (Redis / Celery / DB) that's overkill for
  a single-user local research tool.

## Decision

1. Add a `services/` layer that wraps existing modules. CLI and API both
   call into it. Logic exists in one place; routers stay thin.
2. Define a stable on-disk format for backtest products under
   `reports/sweeps/` and `reports/validations/`, each `run_id` directory
   containing `manifest.json`, `config.json`, and parquet artifacts. CLI
   writes; API reads. Long backtests stay CLI-only.
3. Use FastAPI + Uvicorn + sse-starlette. The `JobRegistry` is an in-process
   dict guarded by a lock with a TTL purge. No persistence, no horizontal
   scaling.
4. Selection is the only "active" endpoint. It runs in a daemon thread
   (not an asyncio task — TestClient cancels per-request loops on return).
   Progress is reported via the registry; clients can poll the GET endpoint
   or subscribe to the SSE stream.
5. Wrap the result cache by `hash(config, as_of_date, symbols, source,
   adjust)`. A repeat call with the same parameters skips the panel read /
   indicator computation and emits a single `done` progress event with
   message "命中缓存".
6. Whitelist local frontend dev origins (`localhost:3000` Next.js,
   `localhost:5173` Vite, both `http://` and `127.0.0.1` forms) for CORS
   preflight by default. Override with `MUCE_API_CORS_ORIGINS` env var or
   `create_app(cors_origins=[...])`. Disallowed origins receive a 400 on
   preflight.

## Implementation

- `services/data_service.py` — symbol search, K-line + indicators, coverage
- `services/selection_service.py` — `run_selection()` with `on_progress` callback and result cache
- `services/reports_service.py` — thin wrapper around `reports.store`
- `reports/schema.py` — `ReportManifest`, `SweepManifest`, `ValidateManifest`
- `reports/store.py` — `write_report`, `list_reports`, `load_report`, `load_artifact`; artifacts under `reports/sweeps/{run_id}/` and `reports/validations/{run_id}/`
- `api/app.py` — FastAPI with `create_app()` factory, RFC 7807 error envelope, DI for cache + reports dir
- 4 routers: `routers/system.py`, `routers/data.py`, `routers/reports.py`, `routers/selection.py`
- `JobRegistry` with SSE progress stream and 1h TTL, no persistence
- Background work via `threading.Thread` (not asyncio — TestClient cancels per-request loops)
- Result cache by config hash; repeat calls skip panel read and emit "命中缓存"
- CLI `quant-backtest sweep` and `quant-backtest validate` now write reports by default; `--no-report` to opt out
- `pyproject.toml`: `api` extra = `fastapi`, `uvicorn[standard]`, `sse-starlette`, `httpx`
- CORS middleware in `api/app.py` reads default whitelist from `_DEFAULT_CORS_ORIGINS` constant; runtime override via `MUCE_API_CORS_ORIGINS=<comma-separated>`
- 27 new tests across `test_services_data`, `test_services_selection`, `test_reports_store`, `test_api_*` (4 of them cover CORS allow / block / env override)
- Full suite: 107 passed, 3 skipped

## Consequences

**Positive**

- One source of truth for data + selection logic, available to whatever
  consumer comes next (web UI, notebook, scheduled job).
- Reports are reproducible artifacts independent of the engine that produced
  them. `git_commit` + `git_dirty` in the manifest preserve provenance.
- Adding the frontend is now a UI problem, not an integration problem.

**Accepted negatives**

- Job state is lost on process restart. Tolerable for v1 (single user,
  selection finishes in seconds for the configurations we care about).
- No multi-user or multi-process scaling. Tolerable for the same reason.
- The selection endpoint has no wall-clock timeout in v1. Cooperative
  cancellation of a numpy/pandas computation is not a clean primitive in
  Python; the README points users to the CLI for long sweeps.
- `hit-rate` and `validation-gap` reports stay on their existing ad-hoc
  output formats for now. Migrating them is a follow-up.

## Notes

- The plan's `cache.inspect()` assumption was wrong (it returns one aggregate,
  not per-symbol). The service iterates `cache.read_symbol` per cached symbol
  for coverage.
- `.gitignore` had an unanchored `reports/` rule that shadow-blocked the new
  Python module `src/quant_backtest/reports/`. Anchored to `/reports/`.
