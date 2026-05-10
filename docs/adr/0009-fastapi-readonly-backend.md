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
