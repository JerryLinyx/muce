# Muce Web Frontend

Next.js 16 + TypeScript + Tailwind v4. Sits on top of the FastAPI backend
(`uv run quant-api`).

## Develop

```bash
npm install
npm run dev         # http://localhost:3000
npm run gen:api     # regenerate types from backend /openapi.json
npm test            # vitest run
npm run build       # production build
```

## Layout

- `app/` — App Router pages and per-page error boundaries
- `components/` — UI primitives + page-specific components
- `lib/api.ts` — fetcher + 16-endpoint client
- `lib/queries.ts` — TanStack Query hooks
- `lib/sse.ts` — `useSelectionJobStream`
- `lib/api-generated.ts` — generated, do not edit
- `lib/api-types.ts` — hand-rolled domain types
- `styles/tokens.css` — color, font, radius, spacing variables

## Conventions

- All page components are `'use client'`. No RSC.
- URL search params are the source of truth for filters; React state for
  local UI only; localStorage for cross-session preferences (not used in v1).
- Charts use `lightweight-charts`. Future heatmaps will use ECharts.
- Errors flow: network → `ApiError` → TanStack Query `error` → row-inline
  `<ErrorBanner>` or `<Toast>` (mutations).
