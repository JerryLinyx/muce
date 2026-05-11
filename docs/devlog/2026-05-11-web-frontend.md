# Web Frontend v1

**Date:** 2026-05-11
**Spec:** [docs/superpowers/specs/2026-05-11-web-frontend-design.md](../superpowers/specs/2026-05-11-web-frontend-design.md)
**Plan:** [docs/superpowers/plans/2026-05-11-web-frontend.md](../superpowers/plans/2026-05-11-web-frontend.md)
**ADR:** [docs/devlog/records/ADR-011_2026-05-11_web-frontend-stack.md](records/ADR-011_2026-05-11_web-frontend-stack.md)

## Summary

Built a Next.js 16 + TypeScript single-page web frontend over the FastAPI
read-only backend. Three pages — symbol dashboard with K-line, daily
selection with SSE progress, and read-only backtest report viewer (both
validate and sweep). Visual style references FinGOAT: tactile warm palette,
low radius, full-bleed chart stage, immersive main area.

## Why

The CLI is the right shape for batch operations and reproducibility but a
poor UI for browsing daily-bar panels, reading sweep tables, or watching
selection progress unfold. Subprocess-ing the CLI from a web layer would
have coupled the HTTP surface to text output. The read-only FastAPI shipped
in 2026-05-10 made a structured JSON surface possible; this devlog covers
the frontend on top.

## What changed

- New `web/` subdirectory: Next.js 16 App Router scaffold, ~60 files across
  `app/`, `components/`, `lib/`, `styles/`, `tests/`.
- Root `.gitignore`: ignore `web/node_modules/`, `.next/`, `out/`,
  `coverage/`, `.turbo/`.
- New docs: this devlog, ADR-011, plan, spec.

## Key decisions

- **Next.js (App Router) + all client components**, no RSC. Local-only tool,
  no SEO / edge-rendering payoff.
- **Reverse-proxy `/api/*` through Next.js** to avoid CORS in the browser
  path; backend CORS remains as a fallback for direct connections.
- **TanStack Query v5 + `openapi-typescript`** for data + type sync. The
  generated types resolve to opaque dicts (FastAPI returns untyped `dict`),
  so a hand-rolled `lib/api-types.ts` layer carries the concrete shapes.
  Retry policy: 4xx no, 5xx twice.
- **`lightweight-charts` v5 for K-line and equity** (TradingView library used
  by FinGOAT). ECharts deferred to v2 for sweep heatmaps.
- **SSE only for selection progress.** Daemon thread on the backend, a
  custom `useSelectionJobStream` hook on the frontend, closes on
  `done` / `failed` / unmount.
- **Tailwind v4 + CSS variables**, no UI library. FinGOAT palette adapted:
  more restrained, single olive accent, A-share convention 红涨绿跌. CSS
  `@theme` bridge in `globals.css` exposes tokens as Tailwind utilities
  (`text-ink`, `bg-chart`, etc.).
- **TopBar 44px, Toolbar 52px, chart stage full-bleed no radius.** Main
  area dominates; chrome stays out of the way.

## Deviations from the original spec

- **Tailwind v4 instead of v3.** `create-next-app` defaults to v4, which
  uses CSS-based `@theme` config instead of a `tailwind.config.ts` file.
  The plan was written assuming v3; we adapted.
- **`next.config.ts` instead of `.mjs`.** Same reason — generator output.
- **No `jsdom@29` peer issue** — installed cleanly.
- **`openapi-typescript` generated types are opaque** because backend
  routes return `dict`. Hand-rolled `api-types.ts` carries the shapes;
  the generated file is kept as a path/operation map for future tightening.
- **All-clientcomponents** — even the empty page shells. Avoids any RSC
  hydration surprises with chart / Radix portal interactions.

## Verification

- `cd web && npm test` — Vitest suite green (21 tests across format /
  url-state / api / sse).
- `cd web && npx tsc --noEmit` — TS clean (strict + `noUncheckedIndexedAccess`).
- Manual smoke: backend running, browse all three pages including a full
  selection round-trip, validate report, and sweep report.

## Follow-ups (out of scope for v1)

- Sweep heatmap (ECharts).
- Dark mode (`:root.theme-dark` hook exists, no styles).
- Mobile responsive (current breakpoint floor ≈ 1280px).
- Job persistence (currently in-process registry).
- More indicators on K-line (KDJ / MACD / Bollinger).
