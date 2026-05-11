---
id: ADR-011
kind: decision
title: Web Frontend Stack — Next.js + TanStack Query + lightweight-charts
date: 2026-05-11
status: accepted
---

# ADR 0011: Web Frontend Stack

## Status

Accepted (2026-05-11).

## Context

The CLI-only Muce tool gained a read-only HTTP surface in 2026-05-10
(ADR-009). A UI was needed to browse data, configure selections, and read
backtest reports. Options considered:

- **Vite + React** (FinGOAT precedent): minimal, fast HMR, no SSR baggage.
- **Next.js (App Router)**: heavier toolchain, but file-based routing,
  built-in dev proxy, and stronger ecosystem for future production deploy.
- **Vue / Svelte / SolidJS**: ruled out — team familiarity skewed React.

For UI library:

- **Ant Design**: most batteries-included Chinese fintech default.
- **shadcn/ui**: own-the-code, design freedom.
- **No UI library, just Tailwind + Radix primitives**: matches FinGOAT,
  smallest surface.

## Decision

1. **Next.js 16 App Router + TypeScript strict** in `web/`. All pages are
   client components; no RSC / SSR.
2. **Reverse-proxy `/api/*` to `http://127.0.0.1:8000`** via
   `next.config.ts` rewrites. Avoids browser CORS path.
3. **Tailwind CSS 4 + custom CSS variables** for design tokens. No UI
   library; Radix primitives only for interactive controls (Select,
   Popover, Dialog, Tooltip, Toast, Checkbox, Collapsible).
4. **Visual style references FinGOAT**: tactile warm palette,
   `--radius-sm/md/lg = 4/6/8px`, full-bleed `chart-stage` with no radius
   or border, single olive accent. A-share convention 红涨绿跌.
5. **TanStack Query v5** for data fetching. queryKey factories in
   `lib/queries.ts`. Retry: 4xx never, 5xx twice.
6. **`openapi-typescript`** generates `lib/api-generated.ts` from FastAPI's
   `/openapi.json`. FastAPI returns untyped `dict` so response types
   resolve to opaque maps; hand-rolled `lib/api-types.ts` carries the
   concrete shapes the backend actually emits.
7. **`lightweight-charts` v5** for K-line and equity curve.
   **ECharts deferred** to v2 (sweep heatmaps).
8. **SSE only for selection progress** via custom `useSelectionJobStream`
   hook. Other endpoints use plain TanStack Query GET. Selection runs in a
   backend daemon thread; stream closes on `done` / `failed` / unmount.
9. **No state library** (Zustand etc.). URL search params for filters,
   React state for local UI.
10. **Vitest + jsdom** for unit tests. **No Playwright** in v1.

## Consequences

**Positive**

- One generated types file binds frontend to the backend's path/operation
  surface; route renames become a compile error.
- Reverse-proxy hides API origin from frontend code; deployment-day config
  changes don't touch components.
- Tailwind + CSS variables means design tokens can be edited in one file
  without touching components.
- `lightweight-charts` is the same library FinGOAT uses; transfer of
  patterns is direct.

**Accepted negatives**

- Next.js with all-client pages is overkill compared to Vite. Mitigation:
  almost no Next.js features beyond `app/` routing + rewrites are used;
  can migrate to Vite later without breaking the directory layout.
- No UI library means each interactive primitive (Combobox, Toast, Dialog)
  is implemented locally. Mitigation: Radix primitives carry the
  accessibility weight; thin wrappers are < 80 lines each.
- TanStack Query in client-only mode loses some RSC integration benefits.
  Acceptable — not used.
- FastAPI's untyped `dict` responses force a hand-rolled domain types file;
  future tightening of the backend (adding `response_model=…`) would let
  `openapi-typescript` carry more weight automatically.

## Notes

- The plan's milestone breakdown produced 50+ files across 6 phases; see
  the plan for the full structure.
- Future ADRs may revisit:
  - ECharts adoption (sweep heatmap, factor attribution radar).
  - Migration to Vite if Next.js features remain unused at v2.
  - Tightening FastAPI response types to make `openapi-typescript` more
    useful.
