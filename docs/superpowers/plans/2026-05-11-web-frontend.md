# Web Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js + TypeScript single-page web frontend over the existing FastAPI read-only backend. Three pages — symbol dashboard, daily selection (with SSE progress), and read-only backtest reports — with a tactile/immersive visual style adapted from FinGOAT.

**Architecture:** All-client-component Next.js 15 App Router app in `web/` subdirectory, reverse-proxying `/api/*` to `http://127.0.0.1:8000`. TanStack Query for data fetching, `openapi-typescript` for type sync, `lightweight-charts` for K-line and equity curves, `react-hook-form + zod` for the selection config form, native EventSource (wrapped in a hook) for selection SSE progress. CSS variables for design tokens (low radius, single olive accent, full-bleed chart stage), Tailwind 4 for utilities, Radix primitives for interactive components.

**Tech Stack:** Next.js 15+, TypeScript (strict), Tailwind CSS 4, `@tanstack/react-query` v5, `lightweight-charts` v5, `@radix-ui/react-*`, `react-hook-form` + `zod`, `dayjs`, `openapi-typescript`. Package manager: **npm** (pnpm not assumed available; `pnpm` substitutes 1:1 if installed).

**Spec:** [docs/superpowers/specs/2026-05-11-web-frontend-design.md](../specs/2026-05-11-web-frontend-design.md)

---

## File Structure

### Created

| Path | Responsibility |
|---|---|
| `web/package.json` | Deps + scripts (`dev`, `build`, `gen:api`, `test`) |
| `web/tsconfig.json` | TS strict mode + `@/*` path alias |
| `web/next.config.mjs` | rewrites `/api/*` → 127.0.0.1:8000, SSE no-buffer header |
| `web/tailwind.config.ts` | Token bridge: CSS vars → Tailwind theme |
| `web/postcss.config.mjs` | Tailwind v4 + autoprefixer |
| `web/vitest.config.ts` | Unit test runner |
| `web/.gitignore` | `node_modules/`, `.next/`, `coverage/` |
| `web/README.md` | "How to run the frontend" |
| `web/app/layout.tsx` | Root shell: TopBar + Providers |
| `web/app/page.tsx` | `/` → `redirect('/dashboard')` |
| `web/app/error.tsx` | Global ErrorBoundary |
| `web/app/globals.css` | Imports tokens.css + Tailwind directives |
| `web/styles/tokens.css` | All CSS variables (color/font/radius/spacing) |
| `web/app/dashboard/page.tsx` | Page ①: symbol K-line dashboard |
| `web/app/dashboard/error.tsx` | Per-page error UI |
| `web/app/selection/page.tsx` | Page ②: selection form + results |
| `web/app/selection/error.tsx` | Per-page error UI |
| `web/app/reports/page.tsx` | Page ③: report list |
| `web/app/reports/error.tsx` | Per-page error UI |
| `web/app/reports/[runId]/page.tsx` | Page ③': report detail (kind-branched) |
| `web/app/reports/[runId]/error.tsx` | Per-page error UI |
| `web/lib/api.ts` | `http<T>` fetcher + 16 endpoint functions + `ApiError` |
| `web/lib/api-generated.ts` | (Generated, do not edit) `openapi-typescript` output |
| `web/lib/api-types.ts` | Thin domain types derived from generated |
| `web/lib/queries.ts` | TanStack Query hooks + queryKey factories |
| `web/lib/query-client.ts` | `QueryClient` singleton with retry policy |
| `web/lib/sse.ts` | `useSelectionJobStream` hook |
| `web/lib/format.ts` | Number / percent / date formatters (zh-CN) |
| `web/lib/url-state.ts` | Typed URL search-params helpers |
| `web/lib/csv.ts` | Client-side CSV download |
| `web/components/topbar/TopBar.tsx` | Slim 44px nav with 3 tabs + health badge |
| `web/components/ui/Button.tsx` | Styled `<button>` |
| `web/components/ui/Input.tsx` | Styled `<input>` |
| `web/components/ui/Select.tsx` | Radix Select wrapper |
| `web/components/ui/Combobox.tsx` | Radix Popover + filterable list (used by SymbolSelector) |
| `web/components/ui/Checkbox.tsx` | Radix Checkbox wrapper |
| `web/components/ui/Toast.tsx` | Radix Toast + `useToast` |
| `web/components/ui/Dialog.tsx` | Radix Dialog wrapper |
| `web/components/ui/Tooltip.tsx` | Radix Tooltip wrapper |
| `web/components/feedback/ErrorBanner.tsx` | Inline error display |
| `web/components/feedback/EmptyState.tsx` | "No data" placeholder |
| `web/components/feedback/Skeleton.tsx` | Loading skeleton bar |
| `web/components/feedback/TableSkeleton.tsx` | N rows of skeleton |
| `web/components/feedback/HealthBadge.tsx` | TopBar corner indicator |
| `web/components/chart/KLineChart.tsx` | Candlestick + MA overlay + volume |
| `web/components/chart/EquityChart.tsx` | Line + drawdown area + trade markers |
| `web/components/dashboard/SymbolSelector.tsx` | Debounced combobox |
| `web/components/dashboard/IndicatorToggles.tsx` | MA/RSI multiselect |
| `web/components/dashboard/SymbolInfoCard.tsx` | Symbol metadata panel |
| `web/components/dashboard/RecentBarsTable.tsx` | Last-N OHLC table |
| `web/components/selection/FactorConfigPanel.tsx` | RHF + zod config form |
| `web/components/selection/SelectionResultsTable.tsx` | Candidates table |
| `web/components/selection/ProgressIndicator.tsx` | Stage label + progress bar |
| `web/components/reports/ReportListTable.tsx` | All reports table |
| `web/components/reports/StatGrid.tsx` | 4 stat cards |
| `web/components/reports/TradesTable.tsx` | Sortable + paginated trades |
| `web/components/reports/SweepResultsTable.tsx` | Sweep results table |
| `web/components/reports/TopCombosCard.tsx` | Top 5 combos summary |
| `web/components/reports/MetaPanel.tsx` | Collapsible run metadata |
| `web/tests/lib/format.test.ts` | Format helper unit tests |
| `web/tests/lib/url-state.test.ts` | URL state helper unit tests |
| `web/tests/lib/api.test.ts` | Fetcher envelope + ApiError tests |
| `web/tests/lib/sse.test.ts` | `useSelectionJobStream` state machine tests |
| `docs/devlog/2026-05-11-web-frontend.md` | Devlog |
| `docs/devlog/records/ADR-011_2026-05-11_web-frontend-stack.md` | ADR |

### Modified

| Path | What changes |
|---|---|
| `.gitignore` | Append `web/node_modules/`, `web/.next/`, `web/out/`, `web/coverage/` |
| `README.md` | Add "Run the frontend" section |
| `README-CN.md` | Add 中文 "前端开发" section |
| `docs/README.md` | Index the new spec, plan, devlog, ADR-011 |
| `docs/devlog/CHANGELOG.md` | Append 2026-05-11 entry |
| `docs/devlog/records/README.md` | Add ADR-011 row |
| `docs/devlog/current/capabilities.md` | Add "Frontend" section |
| `docs/devlog/current/overview.md` | Append frontend to "What Works" |

---

## Phase A — Skeleton

### Task A.1: Initialize Next.js project and root `.gitignore` entries

**Files:**
- Create: `web/` (scaffolded by `create-next-app`)
- Modify: `.gitignore`

- [ ] **Step 1: Scaffold Next.js with strict TS, Tailwind, App Router**

Run from repo root:

```bash
npx --yes create-next-app@latest web \
  --typescript --tailwind --eslint --app \
  --src-dir=false --import-alias='@/*' --turbopack \
  --no-git --use-npm
```

Expected: a `web/` directory containing `package.json`, `next.config.ts` (or `.mjs`), `app/layout.tsx`, `app/page.tsx`, `tailwind.config.ts`, `tsconfig.json`, plus `node_modules/`.

- [ ] **Step 2: Verify Next.js can boot**

Run: `cd web && npm run dev` (let it start, then Ctrl-C after seeing "Ready in …" output)
Expected: server prints `Ready` on http://localhost:3000.

- [ ] **Step 3: Append web build artifacts to root `.gitignore`**

Add at the end of `.gitignore`:

```
# Web frontend (Next.js)
web/node_modules/
web/.next/
web/out/
web/coverage/
web/.turbo/
```

- [ ] **Step 4: Commit**

```bash
git add web/ .gitignore
git commit -m "feat(web): scaffold Next.js app with App Router + Tailwind + TS"
```

### Task A.2: Add core runtime dependencies

**Files:**
- Modify: `web/package.json`

- [ ] **Step 1: Install runtime deps**

Run from `web/`:

```bash
npm install \
  @tanstack/react-query@^5 \
  @tanstack/react-query-devtools@^5 \
  @radix-ui/react-select \
  @radix-ui/react-popover \
  @radix-ui/react-tooltip \
  @radix-ui/react-toast \
  @radix-ui/react-checkbox \
  @radix-ui/react-dialog \
  @radix-ui/react-collapsible \
  lightweight-charts@^5 \
  react-hook-form@^7 \
  zod@^3 \
  dayjs@^1
```

Expected: all packages added under `dependencies`, lockfile updated.

- [ ] **Step 2: Install dev deps**

```bash
npm install --save-dev \
  openapi-typescript@^7 \
  vitest@^2 \
  @vitest/ui \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  jsdom \
  msw@^2 \
  @types/node
```

- [ ] **Step 3: Verify install**

Run: `cd web && npm ls --depth=0`
Expected: no `UNMET DEPENDENCY` lines.

- [ ] **Step 4: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "feat(web): install runtime and test dependencies"
```

### Task A.3: Configure `next.config.mjs` with API rewrites and SSE headers

**Files:**
- Modify: `web/next.config.mjs` (or rename `next.config.ts` if scaffold created TS variant)

- [ ] **Step 1: Replace contents**

If the scaffold created `next.config.ts`, delete it first:

```bash
cd web && rm -f next.config.ts
```

Write `web/next.config.mjs`:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ]
  },
  async headers() {
    return [
      {
        source: '/api/selection/jobs/:id/stream',
        headers: [{ key: 'X-Accel-Buffering', value: 'no' }],
      },
    ]
  },
}

export default nextConfig
```

- [ ] **Step 2: Verify Next.js still boots**

Run: `cd web && npm run dev`
Open `http://localhost:3000/api/health` in a browser (with the FastAPI server running via `uv run quant-api`).
Expected: JSON `{"data":{"status":"ok",...},"meta":{}}` (proxied through Next.js).

Kill the dev server with Ctrl-C.

- [ ] **Step 3: Commit**

```bash
git add web/next.config.mjs
git commit -m "feat(web): reverse-proxy /api/* to FastAPI backend"
```

### Task A.4: TypeScript strict mode + path alias

**Files:**
- Modify: `web/tsconfig.json`

- [ ] **Step 1: Set strict + path alias**

Open `web/tsconfig.json` and ensure these keys are set (merge into existing):

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "ES2022"],
    "module": "esnext",
    "moduleResolution": "bundler",
    "jsx": "preserve",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 2: Verify TS still compiles**

Run: `cd web && npx tsc --noEmit`
Expected: no output (clean compile).

- [ ] **Step 3: Commit**

```bash
git add web/tsconfig.json
git commit -m "feat(web): enable TS strict mode and @/* path alias"
```

### Task A.5: Design tokens (`styles/tokens.css`)

**Files:**
- Create: `web/styles/tokens.css`
- Modify: `web/app/globals.css`

- [ ] **Step 1: Create tokens file**

Write `web/styles/tokens.css`:

```css
:root {
  /* Neutrals */
  --ink-black:      #1a1a14;
  --ink-soft:       #5c5c56;
  --ink-muted:      #8b8a85;

  --canvas:         #f3f1ed;
  --panel:          #ecebea;
  --panel-strong:   #e0d6c5;
  --surface-soft:   #e5e3db;

  /* Chart surface — lighter than canvas for an immersive feel */
  --chart-bg:       #fbfaf6;
  --chart-grid:     rgba(26, 26, 20, 0.06);
  --chart-axis:     rgba(26, 26, 20, 0.35);

  /* Borders / shadows — restrained */
  --border:         rgba(26, 26, 20, 0.08);
  --border-strong:  rgba(26, 26, 20, 0.16);
  --shadow-sm:      0 1px 2px rgba(26, 26, 20, 0.04);
  --shadow-md:      0 4px 12px rgba(26, 26, 20, 0.06);

  /* A-share convention: red up, green down */
  --up:             #c14747;
  --up-soft:        rgba(193, 71, 71, 0.12);
  --down:           #4a7d52;
  --down-soft:      rgba(74, 125, 82, 0.12);

  /* Single accent */
  --accent:         #6b7c5e;
  --accent-soft:    rgba(107, 124, 94, 0.14);

  --warn:           #c08a3a;
  --error:          #cc4b4b;

  /* Type */
  --font-sans: 'Inter', -apple-system, system-ui, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-mono: ui-monospace, 'JetBrains Mono', 'SF Mono', Menlo, monospace;

  --fs-xs:    12px;
  --fs-sm:    13px;
  --fs-base:  14px;
  --fs-md:    15px;
  --fs-lg:    18px;
  --fs-stat:  22px;

  --fw-regular:  400;
  --fw-medium:   500;
  --fw-semibold: 600;

  /* Radius — low and disciplined */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
}

html, body {
  background: var(--canvas);
  color: var(--ink-black);
  font-family: var(--font-sans);
  font-size: var(--fs-base);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

*, *::before, *::after { box-sizing: border-box; }

.numeric {
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.chart-stage {
  border-radius: 0;
  border: none;
  background: var(--chart-bg);
  padding: 0;
  min-height: 480px;
  flex: 1;
}
```

- [ ] **Step 2: Wire tokens into globals.css**

Open `web/app/globals.css` and replace its contents:

```css
@import "../styles/tokens.css";
@import "tailwindcss";

/* Make Inter available globally via next/font (loaded in layout.tsx) */
```

- [ ] **Step 3: Verify dev server picks up tokens**

Run: `cd web && npm run dev`. Open http://localhost:3000.
Expected: page background is the warm gray `#f3f1ed`, body text is dark `#1a1a14`. Stop server.

- [ ] **Step 4: Commit**

```bash
git add web/styles/tokens.css web/app/globals.css
git commit -m "feat(web): design tokens and global stylesheet"
```

### Task A.6: Tailwind config bridges to CSS variables

**Files:**
- Modify: `web/tailwind.config.ts`

- [ ] **Step 1: Replace contents**

Write `web/tailwind.config.ts`:

```ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: 'var(--ink-black)',
          soft: 'var(--ink-soft)',
          muted: 'var(--ink-muted)',
        },
        canvas: 'var(--canvas)',
        panel: {
          DEFAULT: 'var(--panel)',
          strong: 'var(--panel-strong)',
        },
        surface: 'var(--surface-soft)',
        chart: 'var(--chart-bg)',
        border: 'var(--border)',
        'border-strong': 'var(--border-strong)',
        up: 'var(--up)',
        'up-soft': 'var(--up-soft)',
        down: 'var(--down)',
        'down-soft': 'var(--down-soft)',
        accent: 'var(--accent)',
        'accent-soft': 'var(--accent-soft)',
        warn: 'var(--warn)',
        error: 'var(--error)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
      },
      fontFamily: {
        sans: 'var(--font-sans)',
        mono: 'var(--font-mono)',
      },
      fontSize: {
        xs: 'var(--fs-xs)',
        sm: 'var(--fs-sm)',
        base: 'var(--fs-base)',
        md: 'var(--fs-md)',
        lg: 'var(--fs-lg)',
        stat: 'var(--fs-stat)',
      },
    },
  },
  plugins: [],
}

export default config
```

- [ ] **Step 2: Verify a Tailwind class resolves**

Edit `web/app/page.tsx` to:

```tsx
export default function Home() {
  return <main className="p-6 text-ink bg-panel rounded-md">tokens ok</main>
}
```

Run `cd web && npm run dev` and check the page shows `tokens ok` on a soft panel background. Stop server. Revert `page.tsx` to its default content for now (will be replaced in Task A.10).

- [ ] **Step 3: Commit**

```bash
git add web/tailwind.config.ts
git commit -m "feat(web): bridge Tailwind theme to CSS variables"
```

### Task A.7: Vitest setup

**Files:**
- Create: `web/vitest.config.ts`
- Create: `web/tests/setup.ts`
- Modify: `web/package.json` (add scripts)

- [ ] **Step 1: Write Vitest config**

Write `web/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config'
import path from 'node:path'

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    css: false,
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './') },
  },
})
```

Write `web/tests/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 2: Add npm scripts**

In `web/package.json`, ensure the `scripts` block contains:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run",
    "test:watch": "vitest",
    "gen:api": "openapi-typescript http://127.0.0.1:8000/openapi.json -o lib/api-generated.ts"
  }
}
```

- [ ] **Step 3: Write a smoke test to verify wiring**

Create `web/tests/smoke.test.ts`:

```ts
import { describe, it, expect } from 'vitest'

describe('smoke', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2)
  })
})
```

Run: `cd web && npm test`
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add web/vitest.config.ts web/tests/setup.ts web/tests/smoke.test.ts web/package.json
git commit -m "feat(web): vitest + jsdom + testing-library setup"
```

### Task A.8: Generate API types from FastAPI OpenAPI

**Files:**
- Create: `web/lib/api-generated.ts` (generated)
- Create: `web/lib/api-types.ts` (thin domain layer)

- [ ] **Step 1: Start the backend in another shell**

In a separate terminal, from repo root:

```bash
uv run quant-api
```

Confirm `curl http://127.0.0.1:8000/api/health` returns 200.

- [ ] **Step 2: Run codegen**

```bash
cd web && npm run gen:api
```

Expected: `web/lib/api-generated.ts` created (~hundreds of lines, `paths` + `components` exports).

- [ ] **Step 3: Write thin domain layer**

Write `web/lib/api-types.ts`:

```ts
import type { paths, components } from './api-generated'

// Helper to extract response shape
type Json<P extends keyof paths, M extends keyof paths[P]> =
  paths[P][M] extends { responses: { 200: { content: { 'application/json': infer T } } } } ? T : never

// ──────────────── envelopes ────────────────

export type SymbolRow = Json<'/api/symbols', 'get'> extends { data: (infer R)[] } ? R : never
export type SymbolInfo = Json<'/api/symbols/{symbol}', 'get'>['data']
export type BarsResponse = Json<'/api/bars/{symbol}', 'get'>
export type BarsData = BarsResponse['data']
export type BarRow = BarsData['rows'][number]
export type CoverageEntry = Json<'/api/cache/coverage', 'get'>['data'][number]

export type Factor = Json<'/api/selection/factors', 'get'>['data'][number]
export type FactorConfig = Json<'/api/selection/defaults', 'get'>['data']

export type SelectionJobRequest = paths['/api/selection/jobs']['post']['requestBody'] extends
  { content: { 'application/json': infer T } } ? T : never

export type JobState = Json<'/api/selection/jobs/{job_id}', 'get'>['data']
export type SelectionResult = Extract<JobState['result'], { candidates: unknown }> // narrow shape

export type ReportManifest = Json<'/api/reports', 'get'>['data'][number]
export type ReportDetail = Json<'/api/reports/{run_id}', 'get'>['data']
export type ArtifactRows = Json<'/api/reports/{run_id}/equity', 'get'>['data']
```

> If a derived type appears as `never` after generation, it means the OpenAPI shape is wider than expected. Inspect `lib/api-generated.ts`, find the matching `components.schemas.<Name>`, and import it directly. Comment the workaround so it's visible at the next regeneration.

- [ ] **Step 4: Verify types compile**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors. If `SelectionResult` resolves to `never`, fall back to:

```ts
export interface SelectionResult {
  as_of_date: string
  config: Record<string, unknown>
  candidates: Array<{ symbol: string; score: number; factors_hit: string[]; reasons: string }>
  summary: { total_universe: number; passed_min_score: number; top_n_returned: number }
}
```

- [ ] **Step 5: Commit**

```bash
git add web/lib/api-generated.ts web/lib/api-types.ts
git commit -m "feat(web): generate OpenAPI types and thin domain layer"
```

### Task A.9: `lib/api.ts` fetcher + endpoint client

**Files:**
- Create: `web/lib/api.ts`
- Create: `web/tests/lib/api.test.ts`

- [ ] **Step 1: Write failing test**

Write `web/tests/lib/api.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ApiError, api, http } from '@/lib/api'

const originalFetch = globalThis.fetch

beforeEach(() => { globalThis.fetch = vi.fn() as unknown as typeof fetch })
afterEach(() => { globalThis.fetch = originalFetch })

function ok(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } })
}
function err(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
}

describe('http', () => {
  it('unwraps the data envelope', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(ok({ data: { hello: 'world' }, meta: {} }))
    const out = await http<{ hello: string }>('/api/test')
    expect(out).toEqual({ hello: 'world' })
  })

  it('throws ApiError with code + message on 4xx', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      err(404, { error: { code: 'not_found', message: 'no such symbol', details: { symbol: 'XXX' } } })
    )
    await expect(http('/api/test')).rejects.toMatchObject({
      name: 'ApiError',
      code: 'not_found',
      message: 'no such symbol',
      status: 404,
      details: { symbol: 'XXX' },
    })
  })

  it('throws ApiError even when body is not JSON', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('boom', { status: 500 })
    )
    await expect(http('/api/test')).rejects.toBeInstanceOf(ApiError)
  })
})

describe('api.listSymbols', () => {
  it('forwards q and market as query params', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(ok({ data: [], meta: { count: 0 } }))
    await api.listSymbols({ q: '000', market: 'SZ' })
    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
    expect(url).toContain('q=000')
    expect(url).toContain('market=SZ')
  })
})
```

Run: `cd web && npm test`
Expected: FAIL (module `@/lib/api` not found).

- [ ] **Step 2: Implement**

Write `web/lib/api.ts`:

```ts
import type {
  ArtifactRows,
  BarsResponse,
  CoverageEntry,
  Factor,
  FactorConfig,
  JobState,
  ReportDetail,
  ReportManifest,
  SelectionJobRequest,
  SymbolInfo,
  SymbolRow,
} from './api-types'

export class ApiError extends Error {
  readonly name = 'ApiError'
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: unknown,
  ) {
    super(message)
  }
}

type Envelope<T> = { data: T; meta: Record<string, unknown> }

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
  })
  let body: unknown
  try {
    body = await res.json()
  } catch {
    body = undefined
  }
  if (!res.ok) {
    const errBody = (body as { error?: { code?: string; message?: string; details?: unknown } } | undefined)?.error
    throw new ApiError(
      errBody?.code ?? 'unknown',
      errBody?.message ?? res.statusText ?? 'request failed',
      res.status,
      errBody?.details,
    )
  }
  return (body as Envelope<T>).data
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export interface BarsOpts {
  adjust?: string
  start?: string
  end?: string
  indicators?: string  // comma-separated
}

export const api = {
  // system
  health: () => http<{ status: string; cache_root_exists: boolean; reports_dir_exists: boolean }>('/api/health'),
  version: () => http<{ version: string; provider: string }>('/api/version'),

  // data
  listSymbols: (opts: { q?: string; market?: string; limit?: number; offset?: number; adjust?: string } = {}) =>
    http<SymbolRow[]>(`/api/symbols${qs(opts)}`),
  symbolInfo: (symbol: string, adjust = 'qfq') =>
    http<SymbolInfo>(`/api/symbols/${encodeURIComponent(symbol)}${qs({ adjust })}`),
  bars: (symbol: string, opts: BarsOpts = {}) =>
    http<BarsResponse['data']>(`/api/bars/${encodeURIComponent(symbol)}${qs(opts as Record<string, string | undefined>)}`),
  cacheCoverage: (adjust = 'qfq') => http<CoverageEntry[]>(`/api/cache/coverage${qs({ adjust })}`),

  // selection
  factors: () => http<Factor[]>('/api/selection/factors'),
  defaults: () => http<FactorConfig>('/api/selection/defaults'),
  submitSelectionJob: (body: SelectionJobRequest) =>
    http<{ job_id: string }>('/api/selection/jobs', { method: 'POST', body: JSON.stringify(body) }),
  jobStatus: (id: string) =>
    http<JobState>(`/api/selection/jobs/${encodeURIComponent(id)}`),

  // reports
  listReports: (opts: { kind?: string; since?: string; limit?: number } = {}) =>
    http<ReportManifest[]>(`/api/reports${qs(opts as Record<string, string | number | undefined>)}`),
  reportDetail: (id: string) => http<ReportDetail>(`/api/reports/${encodeURIComponent(id)}`),
  reportEquity: (id: string) => http<ArtifactRows>(`/api/reports/${encodeURIComponent(id)}/equity`),
  reportTrades: (id: string) => http<ArtifactRows>(`/api/reports/${encodeURIComponent(id)}/trades`),
  reportSweep: (id: string) => http<ArtifactRows>(`/api/reports/${encodeURIComponent(id)}/sweep`),
}
```

- [ ] **Step 3: Run test**

```bash
cd web && npm test
```

Expected: tests in `api.test.ts` PASS.

- [ ] **Step 4: Commit**

```bash
git add web/lib/api.ts web/tests/lib/api.test.ts
git commit -m "feat(web): http fetcher + 16-endpoint api client with ApiError"
```

### Task A.10: Query client + queryKey factories

**Files:**
- Create: `web/lib/query-client.ts`
- Create: `web/lib/queries.ts`

- [ ] **Step 1: Implement query client**

Write `web/lib/query-client.ts`:

```ts
import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './api'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false
        return failureCount < 2
      },
      refetchOnWindowFocus: false,
      staleTime: 60_000,
    },
    mutations: { retry: false },
  },
})
```

- [ ] **Step 2: Implement queryKey factories + hooks**

Write `web/lib/queries.ts`:

```ts
import { useQuery, useMutation } from '@tanstack/react-query'
import { api, type BarsOpts } from './api'
import type { SelectionJobRequest } from './api-types'

export const queryKeys = {
  health: () => ['health'] as const,
  symbols: (q?: string, market?: string) => ['symbols', { q: q ?? '', market: market ?? '' }] as const,
  symbolInfo: (symbol: string, adjust = 'qfq') => ['symbol-info', symbol, adjust] as const,
  bars: (symbol: string, opts: BarsOpts) => ['bars', symbol, opts] as const,
  coverage: (adjust = 'qfq') => ['cache-coverage', adjust] as const,

  factors: () => ['selection', 'factors'] as const,
  defaults: () => ['selection', 'defaults'] as const,
  job: (id: string) => ['selection', 'jobs', id] as const,

  reports: (kind?: string, since?: string) => ['reports', { kind: kind ?? '', since: since ?? '' }] as const,
  report: (id: string) => ['reports', id] as const,
  reportEquity: (id: string) => ['reports', id, 'equity'] as const,
  reportTrades: (id: string) => ['reports', id, 'trades'] as const,
  reportSweep: (id: string) => ['reports', id, 'sweep'] as const,
}

export const useHealth = () =>
  useQuery({ queryKey: queryKeys.health(), queryFn: api.health, staleTime: 30_000 })

export const useSymbols = (q?: string, market?: string) =>
  useQuery({
    queryKey: queryKeys.symbols(q, market),
    queryFn: () => api.listSymbols({ q, market, limit: 50 }),
    staleTime: 5 * 60_000,
  })

export const useSymbolInfo = (symbol: string | null, adjust = 'qfq') =>
  useQuery({
    queryKey: symbol ? queryKeys.symbolInfo(symbol, adjust) : ['symbol-info', 'idle'],
    queryFn: () => api.symbolInfo(symbol!, adjust),
    enabled: !!symbol,
    staleTime: 5 * 60_000,
  })

export const useBars = (symbol: string | null, opts: BarsOpts) =>
  useQuery({
    queryKey: symbol ? queryKeys.bars(symbol, opts) : ['bars', 'idle'],
    queryFn: () => api.bars(symbol!, opts),
    enabled: !!symbol,
    staleTime: 5 * 60_000,
  })

export const useFactors = () =>
  useQuery({ queryKey: queryKeys.factors(), queryFn: api.factors, staleTime: Infinity })

export const useDefaults = () =>
  useQuery({ queryKey: queryKeys.defaults(), queryFn: api.defaults, staleTime: Infinity })

export const useSubmitSelectionJob = () =>
  useMutation({ mutationFn: (body: SelectionJobRequest) => api.submitSelectionJob(body) })

export const useReports = (kind?: string, since?: string) =>
  useQuery({
    queryKey: queryKeys.reports(kind, since),
    queryFn: () => api.listReports({ kind, since }),
    staleTime: 30_000,
  })

export const useReportDetail = (id: string) =>
  useQuery({ queryKey: queryKeys.report(id), queryFn: () => api.reportDetail(id), staleTime: Infinity })

export const useReportEquity = (id: string) =>
  useQuery({ queryKey: queryKeys.reportEquity(id), queryFn: () => api.reportEquity(id), staleTime: Infinity })

export const useReportTrades = (id: string) =>
  useQuery({ queryKey: queryKeys.reportTrades(id), queryFn: () => api.reportTrades(id), staleTime: Infinity })

export const useReportSweep = (id: string) =>
  useQuery({ queryKey: queryKeys.reportSweep(id), queryFn: () => api.reportSweep(id), staleTime: Infinity })
```

- [ ] **Step 3: Verify TS compiles**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add web/lib/query-client.ts web/lib/queries.ts
git commit -m "feat(web): QueryClient + 11 query/mutation hooks with queryKey factories"
```

### Task A.11: Root layout, TopBar, HealthBadge, redirect

**Files:**
- Create: `web/components/topbar/TopBar.tsx`
- Create: `web/components/feedback/HealthBadge.tsx`
- Modify: `web/app/layout.tsx`
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Write TopBar**

Write `web/components/topbar/TopBar.tsx`:

```tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { HealthBadge } from '@/components/feedback/HealthBadge'

const TABS = [
  { href: '/dashboard', label: '看板' },
  { href: '/selection', label: '选股' },
  { href: '/reports', label: '报告' },
] as const

export function TopBar() {
  const pathname = usePathname()
  return (
    <header
      className="flex items-center justify-between border-b border-border bg-canvas px-5"
      style={{ height: 44 }}
    >
      <div className="flex items-center gap-6">
        <Link href="/dashboard" className="text-md font-semibold tracking-tight">
          Muce <span className="text-ink-muted text-sm">牧策</span>
        </Link>
        <nav className="flex items-center gap-1">
          {TABS.map((tab) => {
            const active = pathname?.startsWith(tab.href)
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={
                  'px-3 py-1.5 text-sm rounded-sm transition-colors ' +
                  (active
                    ? 'bg-accent-soft text-ink'
                    : 'text-ink-soft hover:text-ink hover:bg-surface')
                }
              >
                {tab.label}
              </Link>
            )
          })}
        </nav>
      </div>
      <HealthBadge />
    </header>
  )
}
```

- [ ] **Step 2: Write HealthBadge**

Write `web/components/feedback/HealthBadge.tsx`:

```tsx
'use client'

import { useHealth } from '@/lib/queries'

export function HealthBadge() {
  const { data, isError, isLoading } = useHealth()
  let label = '检查中…'
  let cls = 'text-ink-muted'
  if (isError) { label = '后端离线'; cls = 'text-error' }
  else if (data?.status === 'ok') { label = '后端在线'; cls = 'text-down' }
  return <span className={`text-xs ${cls}`} aria-live="polite">{!isLoading && label}</span>
}
```

- [ ] **Step 3: Write Providers wrapper**

Create `web/components/providers/QueryProvider.tsx`:

```tsx
'use client'

import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { queryClient } from '@/lib/query-client'

export function QueryProvider({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}
```

- [ ] **Step 4: Replace root layout**

Replace `web/app/layout.tsx` with:

```tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { QueryProvider } from '@/components/providers/QueryProvider'
import { TopBar } from '@/components/topbar/TopBar'
import './globals.css'

const inter = Inter({ subsets: ['latin'], display: 'swap', variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Muce 牧策',
  description: 'A 股多因子研究终端',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={inter.variable}>
      <body>
        <QueryProvider>
          <TopBar />
          <main className="min-h-[calc(100vh-44px)]">{children}</main>
        </QueryProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 5: Replace home page with redirect**

Replace `web/app/page.tsx` with:

```tsx
import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/dashboard')
}
```

- [ ] **Step 6: Stub the three pages**

Create `web/app/dashboard/page.tsx`:

```tsx
'use client'

export default function DashboardPage() {
  return <div className="p-6 text-ink-soft">看板:待 Milestone B</div>
}
```

Create `web/app/selection/page.tsx`:

```tsx
'use client'

export default function SelectionPage() {
  return <div className="p-6 text-ink-soft">选股:待 Milestone D</div>
}
```

Create `web/app/reports/page.tsx`:

```tsx
'use client'

export default function ReportsPage() {
  return <div className="p-6 text-ink-soft">报告:待 Milestone C</div>
}
```

- [ ] **Step 7: Smoke test the skeleton**

Make sure backend is running (`uv run quant-api` in another shell), then:

```bash
cd web && npm run dev
```

Open http://localhost:3000.
Expected:
- Redirected to `/dashboard`
- TopBar shows logo + 3 tabs + "后端在线" badge in the corner
- Clicking 选股 / 报告 switches active tab
- No console errors

Stop server.

- [ ] **Step 8: Commit**

```bash
git add web/components/topbar/ web/components/feedback/HealthBadge.tsx web/components/providers/ web/app/layout.tsx web/app/page.tsx web/app/dashboard/page.tsx web/app/selection/page.tsx web/app/reports/page.tsx
git commit -m "feat(web): TopBar, HealthBadge, providers, page shells"
```

### Task A.12: Format helpers + tests

**Files:**
- Create: `web/lib/format.ts`
- Create: `web/tests/lib/format.test.ts`

- [ ] **Step 1: Write failing tests**

Write `web/tests/lib/format.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { fmtPercent, fmtNumber, fmtDate, fmtCompactNumber } from '@/lib/format'

describe('fmtPercent', () => {
  it('renders + sign for positives, 2 decimals', () => {
    expect(fmtPercent(0.1234)).toBe('+12.34%')
    expect(fmtPercent(-0.05)).toBe('-5.00%')
    expect(fmtPercent(0)).toBe('+0.00%')
  })
  it('handles null/undefined', () => {
    expect(fmtPercent(null)).toBe('—')
    expect(fmtPercent(undefined)).toBe('—')
  })
})

describe('fmtNumber', () => {
  it('thousands separators', () => {
    expect(fmtNumber(1234567.89)).toBe('1,234,567.89')
  })
  it('respects decimals', () => {
    expect(fmtNumber(1.234, 1)).toBe('1.2')
  })
  it('handles null', () => {
    expect(fmtNumber(null)).toBe('—')
  })
})

describe('fmtDate', () => {
  it('formats ISO date as YYYY-MM-DD', () => {
    expect(fmtDate('2026-05-11T08:30:00Z')).toBe('2026-05-11')
    expect(fmtDate('2026-05-11')).toBe('2026-05-11')
  })
})

describe('fmtCompactNumber', () => {
  it('uses 万 / 亿 for Chinese magnitudes', () => {
    expect(fmtCompactNumber(12345)).toBe('1.23万')
    expect(fmtCompactNumber(123_456_789)).toBe('1.23亿')
    expect(fmtCompactNumber(999)).toBe('999')
  })
})
```

Run: `cd web && npm test`
Expected: FAIL (module not found).

- [ ] **Step 2: Implement**

Write `web/lib/format.ts`:

```ts
export function fmtPercent(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const pct = value * 100
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(decimals)}%`
}

export function fmtNumber(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return '—'
  return value.slice(0, 10)
}

export function fmtCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const abs = Math.abs(value)
  if (abs >= 1e8) return `${(value / 1e8).toFixed(2)}亿`
  if (abs >= 1e4) return `${(value / 1e4).toFixed(2)}万`
  return Math.round(value).toString()
}
```

- [ ] **Step 3: Verify pass**

```bash
cd web && npm test
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add web/lib/format.ts web/tests/lib/format.test.ts
git commit -m "feat(web): zh-CN number/percent/date/compact formatters"
```

### Task A.13: URL search-params helpers + tests

**Files:**
- Create: `web/lib/url-state.ts`
- Create: `web/tests/lib/url-state.test.ts`

- [ ] **Step 1: Write failing tests**

Write `web/tests/lib/url-state.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { paramsFromSearch, mergeSearch } from '@/lib/url-state'

describe('paramsFromSearch', () => {
  it('returns flat record', () => {
    const sp = new URLSearchParams('symbol=000001.SZ&adjust=qfq&indicators=ma_20,rsi_14')
    expect(paramsFromSearch(sp)).toEqual({
      symbol: '000001.SZ', adjust: 'qfq', indicators: 'ma_20,rsi_14',
    })
  })
})

describe('mergeSearch', () => {
  it('overrides specified keys, preserves others', () => {
    const sp = new URLSearchParams('a=1&b=2')
    expect(mergeSearch(sp, { b: '20', c: '30' })).toBe('a=1&b=20&c=30')
  })
  it('drops keys set to null/empty', () => {
    const sp = new URLSearchParams('a=1&b=2')
    expect(mergeSearch(sp, { a: null, b: '' })).toBe('')
  })
})
```

Run: `cd web && npm test`
Expected: FAIL.

- [ ] **Step 2: Implement**

Write `web/lib/url-state.ts`:

```ts
export function paramsFromSearch(sp: URLSearchParams): Record<string, string> {
  const out: Record<string, string> = {}
  sp.forEach((v, k) => { out[k] = v })
  return out
}

export function mergeSearch(
  sp: URLSearchParams,
  overrides: Record<string, string | null | undefined>,
): string {
  const next = new URLSearchParams(sp)
  for (const [k, v] of Object.entries(overrides)) {
    if (v === null || v === undefined || v === '') next.delete(k)
    else next.set(k, v)
  }
  return next.toString()
}
```

- [ ] **Step 3: Verify**

```bash
cd web && npm test
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add web/lib/url-state.ts web/tests/lib/url-state.test.ts
git commit -m "feat(web): typed URLSearchParams helpers"
```

### Task A.14: Per-page error boundaries + global error

**Files:**
- Create: `web/app/error.tsx`
- Create: `web/app/dashboard/error.tsx`
- Create: `web/app/selection/error.tsx`
- Create: `web/app/reports/error.tsx`

- [ ] **Step 1: Write global error.tsx**

Write `web/app/error.tsx`:

```tsx
'use client'

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="p-8">
      <h1 className="text-lg font-semibold mb-2">页面出错了</h1>
      <p className="text-sm text-ink-soft mb-4">{error.message || '未知错误'}</p>
      <button onClick={reset} className="px-3 py-1.5 text-sm rounded-sm bg-accent-soft text-ink hover:bg-accent hover:text-canvas transition-colors">
        重试
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Write three identical per-page errors**

Each of `web/app/{dashboard,selection,reports}/error.tsx`:

```tsx
'use client'

export default function PageError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="p-8">
      <h2 className="text-md font-medium mb-2">页面出错了</h2>
      <p className="text-sm text-ink-soft mb-4">{error.message || '未知错误'}</p>
      <button onClick={reset} className="px-3 py-1.5 text-sm rounded-sm bg-accent-soft text-ink hover:bg-accent hover:text-canvas transition-colors">
        重试
      </button>
    </div>
  )
}
```

- [ ] **Step 3: Smoke test by throwing in a page**

Edit `web/app/dashboard/page.tsx` temporarily:

```tsx
'use client'
export default function DashboardPage() {
  throw new Error('test error boundary')
}
```

Run dev server, navigate to `/dashboard`.
Expected: page-specific error UI shows "test error boundary" + a 重试 button.

Revert `dashboard/page.tsx` to the original stub.

- [ ] **Step 4: Commit**

```bash
git add web/app/error.tsx web/app/dashboard/error.tsx web/app/selection/error.tsx web/app/reports/error.tsx
git commit -m "feat(web): global and per-page error boundaries"
```

---

## Phase B — Dashboard MVP

### Task B.1: Base UI primitives (Button, Input)

**Files:**
- Create: `web/components/ui/Button.tsx`
- Create: `web/components/ui/Input.tsx`

- [ ] **Step 1: Implement Button**

Write `web/components/ui/Button.tsx`:

```tsx
import * as React from 'react'

type Variant = 'primary' | 'ghost' | 'subtle'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'subtle', size = 'md', className = '', ...props }, ref
) {
  const base = 'inline-flex items-center justify-center font-medium rounded-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const sizes = { sm: 'h-7 px-2.5 text-xs', md: 'h-8 px-3 text-sm' }
  const variants = {
    primary: 'bg-ink text-canvas hover:bg-ink-soft',
    ghost:   'text-ink-soft hover:text-ink hover:bg-surface',
    subtle:  'bg-accent-soft text-ink hover:bg-accent hover:text-canvas',
  }
  return <button ref={ref} className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props} />
})
```

- [ ] **Step 2: Implement Input**

Write `web/components/ui/Input.tsx`:

```tsx
import * as React from 'react'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = '', ...props }, ref) {
    return (
      <input
        ref={ref}
        className={
          'h-8 px-2.5 text-sm rounded-sm bg-canvas border border-border ' +
          'focus:outline-none focus:border-border-strong focus:bg-chart ' +
          'placeholder:text-ink-muted ' + className
        }
        {...props}
      />
    )
  }
)
```

- [ ] **Step 3: Verify TS compiles**

```bash
cd web && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add web/components/ui/Button.tsx web/components/ui/Input.tsx
git commit -m "feat(web): Button and Input primitives"
```

### Task B.2: Toast (Radix) for error notifications

**Files:**
- Create: `web/components/ui/Toast.tsx`
- Modify: `web/components/providers/QueryProvider.tsx`

- [ ] **Step 1: Implement Toast provider + hook**

Write `web/components/ui/Toast.tsx`:

```tsx
'use client'

import * as Toast from '@radix-ui/react-toast'
import * as React from 'react'

type Item = { id: number; title?: string; description: string; tone: 'info' | 'error' }
type Ctx = { add: (t: Omit<Item, 'id'>) => void }

const ToastCtx = React.createContext<Ctx>({ add: () => {} })
export const useToast = () => React.useContext(ToastCtx)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<Item[]>([])
  const add = React.useCallback((t: Omit<Item, 'id'>) => {
    setItems((prev) => [...prev, { ...t, id: Date.now() + Math.random() }])
  }, [])
  return (
    <ToastCtx.Provider value={{ add }}>
      <Toast.Provider duration={4000} swipeDirection="right">
        {children}
        {items.map((item) => (
          <Toast.Root
            key={item.id}
            onOpenChange={(open) => { if (!open) setItems((p) => p.filter((x) => x.id !== item.id)) }}
            className={
              'rounded-md border bg-chart shadow-md p-3 grid gap-1 ' +
              (item.tone === 'error' ? 'border-error/40' : 'border-border')
            }
          >
            {item.title && <Toast.Title className="text-sm font-medium">{item.title}</Toast.Title>}
            <Toast.Description className="text-sm text-ink-soft">{item.description}</Toast.Description>
          </Toast.Root>
        ))}
        <Toast.Viewport className="fixed bottom-4 right-4 flex flex-col gap-2 w-[360px] z-50" />
      </Toast.Provider>
    </ToastCtx.Provider>
  )
}
```

- [ ] **Step 2: Wire into QueryProvider**

Replace `web/components/providers/QueryProvider.tsx` body to wrap children in ToastProvider:

```tsx
'use client'

import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { queryClient } from '@/lib/query-client'
import { ToastProvider } from '@/components/ui/Toast'

export function QueryProvider({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        {children}
        {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
      </ToastProvider>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add web/components/ui/Toast.tsx web/components/providers/QueryProvider.tsx
git commit -m "feat(web): Toast notifications via Radix"
```

### Task B.3: Feedback primitives (Skeleton, EmptyState, ErrorBanner)

**Files:**
- Create: `web/components/feedback/Skeleton.tsx`
- Create: `web/components/feedback/TableSkeleton.tsx`
- Create: `web/components/feedback/EmptyState.tsx`
- Create: `web/components/feedback/ErrorBanner.tsx`

- [ ] **Step 1: Implement Skeleton**

Write `web/components/feedback/Skeleton.tsx`:

```tsx
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={'animate-pulse bg-surface rounded-sm ' + className} />
}
```

- [ ] **Step 2: Implement TableSkeleton**

Write `web/components/feedback/TableSkeleton.tsx`:

```tsx
import { Skeleton } from './Skeleton'

export function TableSkeleton({ rows = 8, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="border border-border rounded-md overflow-hidden">
      <div className="bg-surface flex">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="flex-1 p-2"><Skeleton className="h-3" /></div>
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex border-t border-border">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="flex-1 p-2"><Skeleton className="h-3" /></div>
          ))}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Implement EmptyState**

Write `web/components/feedback/EmptyState.tsx`:

```tsx
export function EmptyState({ title, hint }: { title: string; hint?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-md font-medium text-ink-soft">{title}</div>
      {hint && <div className="text-sm text-ink-muted mt-2 max-w-md">{hint}</div>}
    </div>
  )
}
```

- [ ] **Step 4: Implement ErrorBanner**

Write `web/components/feedback/ErrorBanner.tsx`:

```tsx
export function ErrorBanner({ children }: { children: React.ReactNode }) {
  return (
    <div className="border border-error/30 bg-canvas rounded-md px-3 py-2 text-sm text-error">
      {children}
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add web/components/feedback/
git commit -m "feat(web): Skeleton, TableSkeleton, EmptyState, ErrorBanner"
```

### Task B.4: SymbolSelector (Radix Popover + filterable list)

**Files:**
- Create: `web/components/dashboard/SymbolSelector.tsx`

- [ ] **Step 1: Implement**

Write `web/components/dashboard/SymbolSelector.tsx`:

```tsx
'use client'

import * as Popover from '@radix-ui/react-popover'
import * as React from 'react'
import { Input } from '@/components/ui/Input'
import { useSymbols } from '@/lib/queries'

export function SymbolSelector({
  value,
  onChange,
}: {
  value: string | null
  onChange: (symbol: string) => void
}) {
  const [open, setOpen] = React.useState(false)
  const [query, setQuery] = React.useState('')
  const [debounced, setDebounced] = React.useState('')

  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 300)
    return () => clearTimeout(t)
  }, [query])

  const { data, isLoading } = useSymbols(debounced || undefined)

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          className="h-8 px-2.5 text-sm rounded-sm bg-canvas border border-border min-w-[180px] text-left hover:border-border-strong"
          aria-label="选择标的"
        >
          {value ?? <span className="text-ink-muted">选择标的…</span>}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side="bottom"
          align="start"
          sideOffset={4}
          className="z-50 w-[280px] rounded-md border border-border bg-chart shadow-md p-2"
        >
          <Input
            autoFocus
            placeholder="输入代码前缀,如 000001"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full mb-2"
          />
          <div className="max-h-[260px] overflow-y-auto">
            {isLoading && <div className="px-2 py-1.5 text-xs text-ink-muted">加载中…</div>}
            {!isLoading && data && data.length === 0 && (
              <div className="px-2 py-1.5 text-xs text-ink-muted">无匹配标的</div>
            )}
            {!isLoading && data?.map((row) => (
              <button
                key={row.symbol}
                onClick={() => { onChange(row.symbol); setOpen(false) }}
                className="w-full text-left px-2 py-1.5 text-sm rounded-sm hover:bg-accent-soft flex justify-between"
              >
                <span className="font-mono">{row.symbol}</span>
                <span className="text-xs text-ink-muted">{row.last_cached_date ?? '—'}</span>
              </button>
            ))}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
```

- [ ] **Step 2: Verify TS compiles**

```bash
cd web && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add web/components/dashboard/SymbolSelector.tsx
git commit -m "feat(web): SymbolSelector — debounced searchable combobox"
```

### Task B.5: IndicatorToggles + SymbolInfoCard

**Files:**
- Create: `web/components/dashboard/IndicatorToggles.tsx`
- Create: `web/components/dashboard/SymbolInfoCard.tsx`

- [ ] **Step 1: Implement IndicatorToggles**

Write `web/components/dashboard/IndicatorToggles.tsx`:

```tsx
'use client'

const OPTIONS = [
  { key: 'ma_20', label: 'MA 20' },
  { key: 'ma_60', label: 'MA 60' },
  { key: 'rsi_14', label: 'RSI 14' },
] as const

export function IndicatorToggles({
  value,
  onChange,
}: {
  value: string[]
  onChange: (next: string[]) => void
}) {
  const toggle = (key: string) => {
    onChange(value.includes(key) ? value.filter((k) => k !== key) : [...value, key])
  }
  return (
    <div className="inline-flex border border-border rounded-sm overflow-hidden">
      {OPTIONS.map((opt) => {
        const active = value.includes(opt.key)
        return (
          <button
            key={opt.key}
            onClick={() => toggle(opt.key)}
            className={
              'px-2.5 h-8 text-sm border-r border-border last:border-r-0 ' +
              (active ? 'bg-accent-soft text-ink' : 'text-ink-soft hover:bg-surface')
            }
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Implement SymbolInfoCard**

Write `web/components/dashboard/SymbolInfoCard.tsx`:

```tsx
'use client'

import { useSymbolInfo } from '@/lib/queries'
import { Skeleton } from '@/components/feedback/Skeleton'

export function SymbolInfoCard({ symbol, adjust }: { symbol: string | null; adjust: string }) {
  const { data, isLoading } = useSymbolInfo(symbol, adjust)
  return (
    <div className="border border-border rounded-md bg-chart p-4">
      <div className="text-xs text-ink-muted mb-1">标的信息</div>
      {isLoading ? (
        <div className="space-y-2"><Skeleton className="h-4 w-32" /><Skeleton className="h-3 w-24" /></div>
      ) : data ? (
        <div className="space-y-1.5">
          <div className="text-md font-medium font-mono">{data.symbol}</div>
          <div className="text-sm text-ink-soft">市场:{data.market}</div>
          <div className="text-sm text-ink-soft">最新数据:{data.last_cached_date ?? '—'}</div>
        </div>
      ) : (
        <div className="text-sm text-ink-muted">未选择标的</div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add web/components/dashboard/IndicatorToggles.tsx web/components/dashboard/SymbolInfoCard.tsx
git commit -m "feat(web): IndicatorToggles segmented control and SymbolInfoCard"
```

### Task B.6: KLineChart (lightweight-charts)

**Files:**
- Create: `web/components/chart/KLineChart.tsx`

- [ ] **Step 1: Implement**

Write `web/components/chart/KLineChart.tsx`:

```tsx
'use client'

import * as React from 'react'
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type Time,
} from 'lightweight-charts'
import type { BarRow } from '@/lib/api-types'

interface Props {
  rows: BarRow[]
  indicators: string[]   // ['ma_20', 'rsi_14', ...]
}

export function KLineChart({ rows, indicators }: Props) {
  const containerRef = React.useRef<HTMLDivElement>(null)
  const chartRef = React.useRef<IChartApi | null>(null)

  React.useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { color: '#fbfaf6' },
        textColor: '#5c5c56',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      grid: {
        vertLines: { color: 'rgba(26, 26, 20, 0.06)' },
        horzLines: { color: 'rgba(26, 26, 20, 0.06)' },
      },
      timeScale: { borderColor: 'rgba(26, 26, 20, 0.16)' },
      rightPriceScale: { borderColor: 'rgba(26, 26, 20, 0.16)' },
      crosshair: { mode: 1 },
    })
    chartRef.current = chart

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: '#c14747',
      downColor: '#4a7d52',
      borderUpColor: '#c14747',
      borderDownColor: '#4a7d52',
      wickUpColor: '#c14747',
      wickDownColor: '#4a7d52',
    })
    candle.setData(
      rows.map((r) => ({
        time: r.date as Time,
        open: r.open as number,
        high: r.high as number,
        low: r.low as number,
        close: r.close as number,
      }))
    )

    const volSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      color: 'rgba(107, 124, 94, 0.5)',
    })
    volSeries.priceScale().applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } })
    volSeries.setData(rows.map((r) => ({
      time: r.date as Time,
      value: (r.volume as number) ?? 0,
      color: (r.close as number) >= (r.open as number) ? 'rgba(193, 71, 71, 0.4)' : 'rgba(74, 125, 82, 0.4)',
    })))

    for (const ind of indicators) {
      if (!ind.startsWith('ma_')) continue
      const values = rows
        .map((r) => {
          const v = (r as Record<string, unknown>)[ind]
          return typeof v === 'number' && Number.isFinite(v) ? { time: r.date as Time, value: v } : null
        })
        .filter((v): v is { time: Time; value: number } => v !== null)
      if (values.length === 0) continue
      const line = chart.addSeries(LineSeries, {
        color: ind === 'ma_20' ? '#6b7c5e' : '#c08a3a',
        lineWidth: 1,
      })
      line.setData(values)
    }

    chart.timeScale().fitContent()

    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [rows, indicators])

  return <div ref={containerRef} className="chart-stage w-full h-full" />
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/chart/KLineChart.tsx
git commit -m "feat(web): KLineChart — candlestick + MA overlay + volume"
```

### Task B.7: RecentBarsTable

**Files:**
- Create: `web/components/dashboard/RecentBarsTable.tsx`

- [ ] **Step 1: Implement**

Write `web/components/dashboard/RecentBarsTable.tsx`:

```tsx
'use client'

import type { BarRow } from '@/lib/api-types'
import { fmtNumber, fmtPercent, fmtCompactNumber, fmtDate } from '@/lib/format'

export function RecentBarsTable({ rows }: { rows: BarRow[] }) {
  const tail = rows.slice(-10).reverse()
  return (
    <div className="border border-border rounded-md overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-surface text-ink-soft">
          <tr>
            <th className="text-left  px-2 py-2 font-medium">日期</th>
            <th className="text-right px-2 py-2 font-medium">开</th>
            <th className="text-right px-2 py-2 font-medium">高</th>
            <th className="text-right px-2 py-2 font-medium">低</th>
            <th className="text-right px-2 py-2 font-medium">收</th>
            <th className="text-right px-2 py-2 font-medium">涨跌</th>
            <th className="text-right px-2 py-2 font-medium">成交量</th>
          </tr>
        </thead>
        <tbody>
          {tail.map((r, i) => {
            const prev = tail[i + 1]
            const pct = prev ? ((r.close as number) - (prev.close as number)) / (prev.close as number) : null
            const tone = pct === null ? '' : pct >= 0 ? 'text-up' : 'text-down'
            return (
              <tr key={String(r.date)} className="border-t border-border hover:bg-accent-soft">
                <td className="px-2 py-1.5 numeric">{fmtDate(String(r.date))}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtNumber(r.open as number)}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtNumber(r.high as number)}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtNumber(r.low as number)}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtNumber(r.close as number)}</td>
                <td className={`px-2 py-1.5 numeric text-right ${tone}`}>{fmtPercent(pct)}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtCompactNumber(r.volume as number)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/dashboard/RecentBarsTable.tsx
git commit -m "feat(web): RecentBarsTable — last-10 OHLC with daily change"
```

### Task B.8: Wire dashboard page

**Files:**
- Modify: `web/app/dashboard/page.tsx`

- [ ] **Step 1: Replace contents**

Write `web/app/dashboard/page.tsx`:

```tsx
'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useMemo } from 'react'
import { useBars } from '@/lib/queries'
import { mergeSearch } from '@/lib/url-state'
import { SymbolSelector } from '@/components/dashboard/SymbolSelector'
import { IndicatorToggles } from '@/components/dashboard/IndicatorToggles'
import { SymbolInfoCard } from '@/components/dashboard/SymbolInfoCard'
import { RecentBarsTable } from '@/components/dashboard/RecentBarsTable'
import { KLineChart } from '@/components/chart/KLineChart'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorBanner } from '@/components/feedback/ErrorBanner'
import { TableSkeleton } from '@/components/feedback/TableSkeleton'
import { Skeleton } from '@/components/feedback/Skeleton'

export default function DashboardPage() {
  const router = useRouter()
  const sp = useSearchParams()
  const symbol = sp.get('symbol')
  const adjust = sp.get('adjust') ?? 'qfq'
  const indicatorsParam = sp.get('indicators') ?? 'ma_20'
  const indicators = useMemo(() => indicatorsParam.split(',').filter(Boolean), [indicatorsParam])

  const updateSearch = (overrides: Record<string, string | null>) => {
    const q = mergeSearch(new URLSearchParams(sp.toString()), overrides)
    router.replace(`/dashboard${q ? `?${q}` : ''}`)
  }

  const { data, isLoading, isError, error } = useBars(symbol, {
    adjust,
    indicators: indicators.join(','),
  })

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 44px)' }}>
      {/* Toolbar */}
      <div className="border-b border-border bg-canvas flex items-center gap-3 px-5" style={{ height: 52 }}>
        <SymbolSelector value={symbol} onChange={(s) => updateSearch({ symbol: s })} />
        <div className="inline-flex border border-border rounded-sm overflow-hidden">
          {(['qfq', 'raw'] as const).map((m) => (
            <button
              key={m}
              onClick={() => updateSearch({ adjust: m })}
              className={
                'px-2.5 h-8 text-sm border-r border-border last:border-r-0 ' +
                (adjust === m ? 'bg-accent-soft text-ink' : 'text-ink-soft hover:bg-surface')
              }
            >
              {m === 'qfq' ? '前复权' : '不复权'}
            </button>
          ))}
        </div>
        <IndicatorToggles
          value={indicators}
          onChange={(next) => updateSearch({ indicators: next.join(',') || null })}
        />
      </div>

      {/* Main: chart fills, info sidebar on right */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col">
          {!symbol ? (
            <EmptyState title="请先选择标的" hint="点击左上角搜索框,输入 6 位代码或市场后缀(如 000001.SZ)" />
          ) : isLoading ? (
            <div className="flex-1 m-3"><Skeleton className="w-full h-full" /></div>
          ) : isError ? (
            <div className="p-4"><ErrorBanner>{(error as Error).message}</ErrorBanner></div>
          ) : !data || data.rows.length === 0 ? (
            <EmptyState
              title="该标的尚未下载数据"
              hint={<>请运行 <code className="font-mono text-ink">uv run quant-data download --symbols {symbol}</code></>}
            />
          ) : (
            <div className="flex-1">
              <KLineChart rows={data.rows} indicators={indicators} />
            </div>
          )}
        </div>

        <aside className="w-[300px] border-l border-border bg-canvas p-3 space-y-3 overflow-y-auto">
          <SymbolInfoCard symbol={symbol} adjust={adjust} />
          {!data ? <TableSkeleton rows={6} cols={5} /> : <RecentBarsTable rows={data.rows} />}
        </aside>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Smoke test**

Start backend in another shell:

```bash
uv run quant-api
```

Make sure there's some cached data — if not, run from repo root:

```bash
uv run quant-data download --symbols 000001.SZ --start 20240101 --end 20251231 --adjust qfq
```

Start the dev server: `cd web && npm run dev`. Open http://localhost:3000.

Expected:
- Tabs visible, "看板" active
- Toolbar shows empty SymbolSelector + qfq/raw + indicators toggle
- Center shows "请先选择标的" EmptyState
- Click SymbolSelector → type `000` → pick `000001.SZ` → URL updates to `?symbol=000001.SZ`
- K-line renders with MA20 overlay and volume histogram
- Right sidebar shows 标的信息 + 最近 10 日表
- Toggle indicators / adjust mode updates the chart

Stop the server.

- [ ] **Step 3: Commit**

```bash
git add web/app/dashboard/page.tsx
git commit -m "feat(web): wire dashboard page — chart + toolbar + sidebar"
```

---

## Phase C — Reports list + Validate detail

### Task C.1: ReportListTable

**Files:**
- Create: `web/components/reports/ReportListTable.tsx`

- [ ] **Step 1: Implement**

Write `web/components/reports/ReportListTable.tsx`:

```tsx
'use client'

import Link from 'next/link'
import type { ReportManifest } from '@/lib/api-types'
import { fmtNumber } from '@/lib/format'

export function ReportListTable({ rows }: { rows: ReportManifest[] }) {
  if (rows.length === 0) return null
  return (
    <div className="border border-border rounded-md overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-surface text-ink-soft">
          <tr>
            <th className="text-left px-3 py-2 font-medium">run_id</th>
            <th className="text-left px-3 py-2 font-medium">类型</th>
            <th className="text-left px-3 py-2 font-medium">策略</th>
            <th className="text-right px-3 py-2 font-medium">标的数</th>
            <th className="text-right px-3 py-2 font-medium">用时(s)</th>
            <th className="text-left px-3 py-2 font-medium">创建时间</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.run_id as string} className="border-t border-border hover:bg-accent-soft">
              <td className="px-3 py-2 font-mono text-xs">{(r.run_id as string).slice(0, 24)}</td>
              <td className="px-3 py-2">{r.kind as string}</td>
              <td className="px-3 py-2">{(r as Record<string, unknown>).strategy as string ?? '—'}</td>
              <td className="px-3 py-2 numeric text-right">{Array.isArray(r.symbols) ? r.symbols.length : 0}</td>
              <td className="px-3 py-2 numeric text-right">{fmtNumber(r.elapsed_seconds as number, 1)}</td>
              <td className="px-3 py-2 numeric">{String(r.created_at).replace('T', ' ').replace('Z', '')}</td>
              <td className="px-3 py-2 text-right">
                <Link href={`/reports/${r.run_id}`} className="text-accent hover:underline">详情 →</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/reports/ReportListTable.tsx
git commit -m "feat(web): ReportListTable component"
```

### Task C.2: Reports list page

**Files:**
- Modify: `web/app/reports/page.tsx`

- [ ] **Step 1: Implement**

Write `web/app/reports/page.tsx`:

```tsx
'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useReports } from '@/lib/queries'
import { mergeSearch } from '@/lib/url-state'
import { ReportListTable } from '@/components/reports/ReportListTable'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorBanner } from '@/components/feedback/ErrorBanner'
import { TableSkeleton } from '@/components/feedback/TableSkeleton'

const KINDS = [
  { key: '', label: '全部' },
  { key: 'sweep', label: 'Sweep' },
  { key: 'validate', label: 'Validate' },
] as const

export default function ReportsPage() {
  const router = useRouter()
  const sp = useSearchParams()
  const kind = sp.get('kind') ?? ''
  const since = sp.get('since') ?? ''

  const update = (overrides: Record<string, string | null>) => {
    const q = mergeSearch(new URLSearchParams(sp.toString()), overrides)
    router.replace(`/reports${q ? `?${q}` : ''}`)
  }

  const { data, isLoading, isError, error } = useReports(kind || undefined, since || undefined)

  return (
    <div className="flex flex-col">
      <div className="border-b border-border bg-canvas flex items-center gap-3 px-5" style={{ height: 52 }}>
        <div className="inline-flex border border-border rounded-sm overflow-hidden">
          {KINDS.map((k) => (
            <button
              key={k.key}
              onClick={() => update({ kind: k.key || null })}
              className={
                'px-2.5 h-8 text-sm border-r border-border last:border-r-0 ' +
                ((kind || '') === k.key ? 'bg-accent-soft text-ink' : 'text-ink-soft hover:bg-surface')
              }
            >
              {k.label}
            </button>
          ))}
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-ink-soft">
          自:
          <input
            type="date"
            value={since}
            onChange={(e) => update({ since: e.target.value || null })}
            className="h-8 px-2 rounded-sm border border-border bg-canvas text-sm"
          />
        </label>
      </div>

      <div className="p-5">
        {isLoading ? (
          <TableSkeleton rows={6} cols={7} />
        ) : isError ? (
          <ErrorBanner>{(error as Error).message}</ErrorBanner>
        ) : !data || data.length === 0 ? (
          <EmptyState
            title="还没有报告"
            hint={<>运行 <code className="font-mono text-ink">uv run quant-backtest sweep …</code> 或 <code className="font-mono text-ink">validate …</code> 生成。</>}
          />
        ) : (
          <ReportListTable rows={data} />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Smoke test**

With backend running and at least one report on disk (from a previous `quant-backtest sweep` or `validate` run), visit `/reports`.
Expected: table lists at least one row with run_id and 详情 link.

- [ ] **Step 3: Commit**

```bash
git add web/app/reports/page.tsx
git commit -m "feat(web): reports list page with kind/since filters"
```

### Task C.3: StatGrid component

**Files:**
- Create: `web/components/reports/StatGrid.tsx`

- [ ] **Step 1: Implement**

Write `web/components/reports/StatGrid.tsx`:

```tsx
import { fmtNumber, fmtPercent } from '@/lib/format'

export interface Stat {
  label: string
  value: number | null | undefined
  format: 'percent' | 'number' | 'int'
  tone?: 'auto' | 'neutral'  // auto = red positive / green negative for returns
  decimals?: number
}

export function StatGrid({ stats }: { stats: Stat[] }) {
  return (
    <div className="grid grid-cols-4 gap-3">
      {stats.map((s) => {
        let display: string
        let tone = 'text-ink'
        if (s.value == null) {
          display = '—'
        } else if (s.format === 'percent') {
          display = fmtPercent(s.value, s.decimals ?? 2)
          if (s.tone === 'auto') tone = s.value >= 0 ? 'text-up' : 'text-down'
        } else if (s.format === 'int') {
          display = Math.round(s.value).toLocaleString('en-US')
        } else {
          display = fmtNumber(s.value, s.decimals ?? 2)
        }
        return (
          <div key={s.label} className="border border-border rounded-md bg-chart p-3">
            <div className="text-xs text-ink-muted mb-1">{s.label}</div>
            <div className={`text-stat numeric ${tone}`}>{display}</div>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/reports/StatGrid.tsx
git commit -m "feat(web): StatGrid for summary metrics"
```

### Task C.4: TradesTable (sortable + paginated)

**Files:**
- Create: `web/components/reports/TradesTable.tsx`

- [ ] **Step 1: Implement**

Write `web/components/reports/TradesTable.tsx`:

```tsx
'use client'

import * as React from 'react'
import { Button } from '@/components/ui/Button'
import { fmtNumber, fmtPercent, fmtDate } from '@/lib/format'

type Row = Record<string, unknown>

const COLUMNS: { key: string; label: string; align: 'left' | 'right'; format: 'date' | 'num' | 'pct' | 'int' | 'text' }[] = [
  { key: 'trade_id', label: 'ID', align: 'right', format: 'int' },
  { key: 'symbol', label: '标的', align: 'left', format: 'text' },
  { key: 'direction', label: '方向', align: 'left', format: 'text' },
  { key: 'open_date', label: '开仓', align: 'left', format: 'date' },
  { key: 'close_date', label: '平仓', align: 'left', format: 'date' },
  { key: 'open_price', label: '开仓价', align: 'right', format: 'num' },
  { key: 'close_price', label: '平仓价', align: 'right', format: 'num' },
  { key: 'size', label: '数量', align: 'right', format: 'int' },
  { key: 'pnl', label: '盈亏', align: 'right', format: 'num' },
  { key: 'pnl_pct', label: '收益率', align: 'right', format: 'pct' },
]

function formatCell(value: unknown, fmt: typeof COLUMNS[number]['format']): string {
  if (value == null) return '—'
  if (fmt === 'date') return fmtDate(String(value))
  if (fmt === 'num') return fmtNumber(Number(value), 2)
  if (fmt === 'int') return Math.round(Number(value)).toLocaleString('en-US')
  if (fmt === 'pct') return fmtPercent(Number(value))
  return String(value)
}

export function TradesTable({ rows }: { rows: Row[] }) {
  const [sortKey, setSortKey] = React.useState<string>('trade_id')
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc')
  const [page, setPage] = React.useState(0)
  const PAGE = 20

  const sorted = React.useMemo(() => {
    const out = [...rows]
    out.sort((a, b) => {
      const va = a[sortKey]; const vb = b[sortKey]
      if (va == null) return 1
      if (vb == null) return -1
      const cmp = typeof va === 'number' && typeof vb === 'number'
        ? va - vb : String(va).localeCompare(String(vb))
      return sortDir === 'asc' ? cmp : -cmp
    })
    return out
  }, [rows, sortKey, sortDir])

  const pageRows = sorted.slice(page * PAGE, (page + 1) * PAGE)
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE))

  return (
    <div className="space-y-2">
      <div className="border border-border rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface text-ink-soft">
            <tr>
              {COLUMNS.map((c) => {
                const active = sortKey === c.key
                return (
                  <th
                    key={c.key}
                    onClick={() => {
                      if (active) setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
                      else { setSortKey(c.key); setSortDir('asc') }
                    }}
                    className={`px-2.5 py-2 cursor-pointer font-medium select-none ` +
                      (c.align === 'right' ? 'text-right' : 'text-left')}
                  >
                    {c.label}{active && (sortDir === 'asc' ? ' ▲' : ' ▼')}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((r, i) => (
              <tr key={`${r.trade_id ?? i}-${i}`} className="border-t border-border hover:bg-accent-soft">
                {COLUMNS.map((c) => (
                  <td key={c.key} className={`px-2.5 py-1.5 numeric ` + (c.align === 'right' ? 'text-right' : 'text-left')}>
                    {formatCell(r[c.key], c.format)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-xs text-ink-soft">
        <span>共 {sorted.length} 条</span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>上一页</Button>
          <span>{page + 1} / {totalPages}</span>
          <Button size="sm" variant="ghost" disabled={page >= totalPages - 1} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}>下一页</Button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/reports/TradesTable.tsx
git commit -m "feat(web): TradesTable — sortable + paginated"
```

### Task C.5: EquityChart

**Files:**
- Create: `web/components/chart/EquityChart.tsx`

- [ ] **Step 1: Implement**

Write `web/components/chart/EquityChart.tsx`:

```tsx
'use client'

import * as React from 'react'
import {
  createChart,
  LineSeries,
  AreaSeries,
  type IChartApi,
  type Time,
} from 'lightweight-charts'

type EquityRow = Record<string, unknown>

export function EquityChart({ rows }: { rows: EquityRow[] }) {
  const containerRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { color: '#fbfaf6' },
        textColor: '#5c5c56',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      grid: {
        vertLines: { color: 'rgba(26, 26, 20, 0.06)' },
        horzLines: { color: 'rgba(26, 26, 20, 0.06)' },
      },
      timeScale: { borderColor: 'rgba(26, 26, 20, 0.16)' },
      rightPriceScale: { borderColor: 'rgba(26, 26, 20, 0.16)' },
      crosshair: { mode: 1 },
    })

    const equitySeries = chart.addSeries(LineSeries, { color: '#6b7c5e', lineWidth: 2 })
    equitySeries.setData(
      rows
        .map((r) => {
          const t = String(r.date).slice(0, 10) as Time
          const v = Number(r.equity)
          return Number.isFinite(v) ? { time: t, value: v } : null
        })
        .filter((v): v is { time: Time; value: number } => v !== null)
    )

    if (rows.length && rows[0] && 'drawdown' in rows[0]) {
      const dd = chart.addSeries(AreaSeries, {
        priceScaleId: 'left',
        topColor: 'rgba(193, 71, 71, 0.18)',
        bottomColor: 'rgba(193, 71, 71, 0.02)',
        lineColor: 'rgba(193, 71, 71, 0.6)',
        lineWidth: 1,
      })
      dd.setData(
        rows
          .map((r) => {
            const t = String(r.date).slice(0, 10) as Time
            const v = Number(r.drawdown)
            return Number.isFinite(v) ? { time: t, value: v } : null
          })
          .filter((v): v is { time: Time; value: number } => v !== null)
      )
      chart.priceScale('left').applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } })
    }

    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [rows])

  return <div ref={containerRef} className="chart-stage w-full" style={{ height: 360 }} />
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/chart/EquityChart.tsx
git commit -m "feat(web): EquityChart — equity line + drawdown area"
```

### Task C.6: MetaPanel (collapsible run metadata)

**Files:**
- Create: `web/components/reports/MetaPanel.tsx`

- [ ] **Step 1: Implement**

Write `web/components/reports/MetaPanel.tsx`:

```tsx
'use client'

import * as Collapsible from '@radix-ui/react-collapsible'
import { useState } from 'react'

export function MetaPanel({ manifest }: { manifest: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible.Root open={open} onOpenChange={setOpen}>
      <Collapsible.Trigger className="text-sm text-ink-soft hover:text-ink underline">
        {open ? '隐藏' : '显示'}元信息
      </Collapsible.Trigger>
      <Collapsible.Content className="mt-2">
        <div className="border border-border rounded-md bg-chart p-3">
          <table className="w-full text-xs">
            <tbody>
              {['run_id', 'kind', 'created_at', 'elapsed_seconds', 'git_commit', 'git_dirty'].map((key) => (
                <tr key={key}>
                  <td className="text-ink-muted py-0.5 pr-3 align-top">{key}</td>
                  <td className="font-mono py-0.5">{String(manifest[key] ?? '—')}</td>
                </tr>
              ))}
              <tr>
                <td className="text-ink-muted py-0.5 pr-3 align-top">data_range</td>
                <td className="font-mono py-0.5">{JSON.stringify(manifest.data_range ?? null)}</td>
              </tr>
              <tr>
                <td className="text-ink-muted py-0.5 pr-3 align-top">symbols</td>
                <td className="font-mono py-0.5">{Array.isArray(manifest.symbols) ? manifest.symbols.join(', ') : '—'}</td>
              </tr>
            </tbody>
          </table>
          <details className="mt-2">
            <summary className="text-xs text-ink-muted cursor-pointer">完整 manifest JSON</summary>
            <pre className="text-xs mt-2 max-h-[280px] overflow-auto bg-canvas p-2 rounded-sm border border-border">
              {JSON.stringify(manifest, null, 2)}
            </pre>
          </details>
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/reports/MetaPanel.tsx
git commit -m "feat(web): MetaPanel collapsible report metadata"
```

### Task C.7: Report detail page (validate branch)

**Files:**
- Create: `web/app/reports/[runId]/page.tsx`

- [ ] **Step 1: Implement**

Write `web/app/reports/[runId]/page.tsx`:

```tsx
'use client'

import { use } from 'react'
import Link from 'next/link'
import { useReportDetail, useReportEquity, useReportTrades, useReportSweep } from '@/lib/queries'
import { StatGrid, type Stat } from '@/components/reports/StatGrid'
import { TradesTable } from '@/components/reports/TradesTable'
import { EquityChart } from '@/components/chart/EquityChart'
import { MetaPanel } from '@/components/reports/MetaPanel'
import { ErrorBanner } from '@/components/feedback/ErrorBanner'
import { Skeleton } from '@/components/feedback/Skeleton'

export default function ReportDetailPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = use(params)
  const { data: manifest, isLoading, isError, error } = useReportDetail(runId)

  if (isLoading) return <div className="p-5"><Skeleton className="h-6 w-64 mb-3" /><Skeleton className="h-32 w-full" /></div>
  if (isError) return <div className="p-5"><ErrorBanner>{(error as Error).message}</ErrorBanner></div>
  if (!manifest) return null

  const m = manifest as unknown as Record<string, unknown>
  const kind = m.kind as string

  return (
    <div className="p-5 space-y-5">
      <div className="flex items-center gap-3 text-sm">
        <Link href="/reports" className="text-accent hover:underline">{'<'} 返回列表</Link>
        <span className="text-ink-muted">·</span>
        <span className="font-mono text-xs">{runId}</span>
      </div>

      {kind === 'validate' ? <ValidateBranch runId={runId} manifest={m} /> : null}
      {kind === 'sweep' ? <SweepBranchPlaceholder /> : null}

      <MetaPanel manifest={m} />
    </div>
  )
}

function ValidateBranch({ runId, manifest }: { runId: string; manifest: Record<string, unknown> }) {
  const summary = (manifest.summary_metrics ?? {}) as Record<string, number>
  const stats: Stat[] = [
    { label: '总收益', value: summary.total_return, format: 'percent', tone: 'auto' },
    { label: '夏普', value: summary.sharpe, format: 'number', decimals: 2 },
    { label: '最大回撤', value: summary.max_drawdown, format: 'percent', tone: 'auto' },
    { label: '交易数', value: summary.trades, format: 'int' },
  ]
  const equity = useReportEquity(runId)
  const trades = useReportTrades(runId)
  return (
    <>
      <div className="text-md text-ink-soft">
        策略:{String(manifest.strategy ?? '—')} · 信号 {String(manifest.signal_adjust ?? '—')} / 执行 {String(manifest.execution_adjust ?? '—')}
      </div>
      <StatGrid stats={stats} />
      {equity.isLoading ? <Skeleton className="h-[360px] w-full" /> :
        equity.data ? <EquityChart rows={equity.data.rows as Record<string, unknown>[]} /> :
        null}
      <div>
        <div className="text-md font-medium mb-2">交易明细</div>
        {trades.isLoading ? <Skeleton className="h-40 w-full" /> :
          trades.data ? <TradesTable rows={trades.data.rows as Record<string, unknown>[]} /> :
          null}
      </div>
    </>
  )
}

function SweepBranchPlaceholder() {
  return <div className="text-ink-soft text-sm">(Sweep 详情见 Milestone E)</div>
}
```

- [ ] **Step 2: Smoke test**

With a `validate` report on disk (run `uv run quant-backtest validate --symbols 000001.SZ --strategy sma-cross` if needed), open the detail link from `/reports`.
Expected:
- Returns to list link visible
- 策略 line, 4 stat cards, equity chart, trades table all render
- Toggle "显示元信息" reveals the meta panel

- [ ] **Step 3: Commit**

```bash
git add web/app/reports/[runId]/page.tsx
git commit -m "feat(web): report detail page with validate branch"
```

---

## Phase D — Selection page with SSE

### Task D.1: SSE hook with state machine + tests

**Files:**
- Create: `web/lib/sse.ts`
- Create: `web/tests/lib/sse.test.ts`

- [ ] **Step 1: Write failing tests**

Write `web/tests/lib/sse.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSelectionJobStream } from '@/lib/sse'

class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  listeners: Record<string, ((e: { data: string }) => void)[]> = {}
  onerror: (() => void) | null = null
  closed = false
  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }
  addEventListener(event: string, cb: (e: { data: string }) => void) {
    this.listeners[event] = this.listeners[event] ?? []
    this.listeners[event].push(cb)
  }
  removeEventListener() {}
  close() { this.closed = true }
  emit(event: string, data: unknown) {
    for (const cb of this.listeners[event] ?? []) cb({ data: JSON.stringify(data) })
  }
}

beforeEach(() => {
  MockEventSource.instances = []
  ;(globalThis as unknown as { EventSource: typeof MockEventSource }).EventSource = MockEventSource
})

describe('useSelectionJobStream', () => {
  it('starts in idle when jobId is null', () => {
    const { result } = renderHook(() => useSelectionJobStream(null))
    expect(result.current.status).toBe('idle')
  })

  it('transitions through running -> done', () => {
    const { result } = renderHook(() => useSelectionJobStream('JOB1'))
    expect(result.current.status).toBe('running')
    const es = MockEventSource.instances[0]
    act(() => es.emit('progress', { stage: 'load_panel', progress: 0.1, message: '加载...' }))
    expect(result.current).toMatchObject({ status: 'running', stage: 'load_panel', progress: 0.1 })
    act(() => es.emit('done', { stage: 'done', progress: 1, result: { candidates: [], summary: {} } }))
    expect(result.current.status).toBe('done')
    expect(es.closed).toBe(true)
  })

  it('handles failed event', () => {
    const { result } = renderHook(() => useSelectionJobStream('JOB2'))
    const es = MockEventSource.instances[0]
    act(() => es.emit('failed', { error: 'boom' }))
    expect(result.current).toMatchObject({ status: 'failed', error: 'boom' })
    expect(es.closed).toBe(true)
  })

  it('closes when jobId changes or unmounts', () => {
    const { rerender, unmount } = renderHook(({ id }) => useSelectionJobStream(id), { initialProps: { id: 'A' } })
    expect(MockEventSource.instances).toHaveLength(1)
    expect(MockEventSource.instances[0].closed).toBe(false)
    rerender({ id: 'B' })
    expect(MockEventSource.instances[0].closed).toBe(true)
    expect(MockEventSource.instances).toHaveLength(2)
    unmount()
    expect(MockEventSource.instances[1].closed).toBe(true)
  })
})
```

Run: `cd web && npm test`
Expected: FAIL (module not found).

- [ ] **Step 2: Implement**

Write `web/lib/sse.ts`:

```ts
'use client'

import { useEffect, useState } from 'react'
import type { SelectionResult } from './api-types'

export type JobUIState =
  | { status: 'idle' }
  | { status: 'running'; stage: string; progress: number; message: string }
  | { status: 'done'; result: SelectionResult }
  | { status: 'failed'; error: string }

export function useSelectionJobStream(jobId: string | null): JobUIState {
  const [state, setState] = useState<JobUIState>({ status: 'idle' })

  useEffect(() => {
    if (!jobId) {
      setState({ status: 'idle' })
      return
    }
    setState({ status: 'running', stage: 'pending', progress: 0, message: '提交中...' })

    const es = new EventSource(`/api/selection/jobs/${jobId}/stream`)

    es.addEventListener('progress', (e) => {
      const p = JSON.parse((e as MessageEvent).data) as { stage: string; progress: number; message: string }
      setState({ status: 'running', stage: p.stage, progress: p.progress, message: p.message })
    })
    es.addEventListener('done', (e) => {
      const p = JSON.parse((e as MessageEvent).data) as { result: SelectionResult }
      setState({ status: 'done', result: p.result })
      es.close()
    })
    es.addEventListener('failed', (e) => {
      const p = JSON.parse((e as MessageEvent).data) as { error: string }
      setState({ status: 'failed', error: p.error })
      es.close()
    })

    return () => es.close()
  }, [jobId])

  return state
}
```

- [ ] **Step 3: Run tests**

```bash
cd web && npm test
```

Expected: all 4 PASS.

- [ ] **Step 4: Commit**

```bash
git add web/lib/sse.ts web/tests/lib/sse.test.ts
git commit -m "feat(web): useSelectionJobStream SSE hook with state machine"
```

### Task D.2: FactorConfigPanel (RHF + zod)

**Files:**
- Create: `web/components/selection/FactorConfigPanel.tsx`

- [ ] **Step 1: Implement**

Write `web/components/selection/FactorConfigPanel.tsx`:

```tsx
'use client'

import * as React from 'react'
import { useForm } from 'react-hook-form'
import { useFactors, useDefaults } from '@/lib/queries'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/feedback/Skeleton'

export interface SelectionFormValues {
  as_of_date: string | null
  min_score: number
  top_n: number
  exclude_suspended: boolean
  exclude_st: boolean
  require_factors: string[]
  exclude_factors: string[]
  // Tunable params (advanced):
  ma_short: number
  ma_long: number
  rsi_window: number
  rsi_threshold: number
  volume_window: number
  volume_multiplier: number
}

export function FactorConfigPanel({
  onSubmit,
  disabled,
}: {
  onSubmit: (values: SelectionFormValues) => void
  disabled?: boolean
}) {
  const factors = useFactors()
  const defaults = useDefaults()
  const [advanced, setAdvanced] = React.useState(false)

  const form = useForm<SelectionFormValues>({
    values: defaults.data ? {
      as_of_date: null,
      min_score: (defaults.data as Record<string, number>).min_score,
      top_n: (defaults.data as Record<string, number>).top_n,
      exclude_suspended: (defaults.data as Record<string, boolean>).exclude_suspended,
      exclude_st: (defaults.data as Record<string, boolean>).exclude_st,
      require_factors: (defaults.data as Record<string, string[]>).require_factors ?? [],
      exclude_factors: (defaults.data as Record<string, string[]>).exclude_factors ?? [],
      ma_short: (defaults.data as Record<string, number>).ma_short,
      ma_long: (defaults.data as Record<string, number>).ma_long,
      rsi_window: (defaults.data as Record<string, number>).rsi_window,
      rsi_threshold: (defaults.data as Record<string, number>).rsi_threshold,
      volume_window: (defaults.data as Record<string, number>).volume_window,
      volume_multiplier: (defaults.data as Record<string, number>).volume_multiplier,
    } : undefined,
  })

  if (factors.isLoading || defaults.isLoading) {
    return <div className="space-y-3"><Skeleton className="h-6 w-32" /><Skeleton className="h-32 w-full" /></div>
  }
  if (!factors.data || !defaults.data) return null

  const toggleArray = (key: 'require_factors' | 'exclude_factors', factor: string) => {
    const cur = form.getValues(key)
    const next = cur.includes(factor) ? cur.filter((f) => f !== factor) : [...cur, factor]
    form.setValue(key, next)
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5 p-4 text-sm">
      <Section title="截止日期">
        <input
          type="date"
          {...form.register('as_of_date')}
          className="h-8 px-2 rounded-sm border border-border bg-canvas text-sm w-full"
        />
        <div className="text-xs text-ink-muted mt-1">留空使用最近交易日</div>
      </Section>

      <Section title="启用因子">
        <div className="space-y-1.5">
          {factors.data.map((f) => (
            <div key={(f as Record<string, string>).key} className="text-xs text-ink-soft">
              {(f as Record<string, string>).name_cn}
              <span className="text-ink-muted ml-1 font-mono">({(f as Record<string, string>).key})</span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="排序">
        <Row label="min_score">
          <Input type="number" {...form.register('min_score', { valueAsNumber: true, min: 0, max: 6 })} className="w-20" />
        </Row>
        <Row label="top_n">
          <Input type="number" {...form.register('top_n', { valueAsNumber: true, min: 1 })} className="w-20" />
        </Row>
      </Section>

      <Section title="过滤">
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" {...form.register('exclude_suspended')} />排除停牌
        </label>
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" {...form.register('exclude_st')} />排除 ST
        </label>
        <div className="mt-2">
          <div className="text-xs text-ink-muted mb-1">必须命中的因子(require)</div>
          <div className="flex flex-wrap gap-1">
            {factors.data.map((f) => {
              const key = (f as Record<string, string>).key
              const active = form.watch('require_factors').includes(key)
              return (
                <button type="button" key={key}
                  onClick={() => toggleArray('require_factors', key)}
                  className={'px-2 py-0.5 text-xs rounded-sm border ' +
                    (active ? 'border-accent bg-accent-soft' : 'border-border text-ink-muted')}>
                  {(f as Record<string, string>).name_cn}
                </button>
              )
            })}
          </div>
        </div>
        <div className="mt-2">
          <div className="text-xs text-ink-muted mb-1">必须排除的因子(exclude)</div>
          <div className="flex flex-wrap gap-1">
            {factors.data.map((f) => {
              const key = (f as Record<string, string>).key
              const active = form.watch('exclude_factors').includes(key)
              return (
                <button type="button" key={key}
                  onClick={() => toggleArray('exclude_factors', key)}
                  className={'px-2 py-0.5 text-xs rounded-sm border ' +
                    (active ? 'border-error bg-canvas text-error' : 'border-border text-ink-muted')}>
                  {(f as Record<string, string>).name_cn}
                </button>
              )
            })}
          </div>
        </div>
      </Section>

      <button type="button" onClick={() => setAdvanced((v) => !v)} className="text-xs text-ink-soft hover:text-ink underline">
        {advanced ? '收起调参' : '展开调参'}
      </button>
      {advanced && (
        <Section title="调参(默认无需改)">
          <Row label="ma_short"><Input type="number" {...form.register('ma_short', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="ma_long"><Input type="number" {...form.register('ma_long', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="rsi_window"><Input type="number" {...form.register('rsi_window', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="rsi_threshold"><Input type="number" step="0.1" {...form.register('rsi_threshold', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="volume_window"><Input type="number" {...form.register('volume_window', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="volume_multiplier"><Input type="number" step="0.1" {...form.register('volume_multiplier', { valueAsNumber: true })} className="w-20" /></Row>
        </Section>
      )}

      <div className="flex gap-2 pt-2 border-t border-border">
        <Button type="submit" variant="primary" disabled={disabled} className="flex-1">开始选股 ▶</Button>
        <Button type="button" variant="ghost" onClick={() => form.reset()} disabled={disabled}>恢复默认</Button>
      </div>
    </form>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-xs uppercase tracking-wide text-ink-muted mb-1">{title}</legend>
      {children}
    </fieldset>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex items-center justify-between gap-2 text-xs text-ink-soft">
      <span className="font-mono">{label}</span>
      {children}
    </label>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/selection/FactorConfigPanel.tsx
git commit -m "feat(web): FactorConfigPanel — RHF form for selection config"
```

### Task D.3: ProgressIndicator

**Files:**
- Create: `web/components/selection/ProgressIndicator.tsx`

- [ ] **Step 1: Implement**

Write `web/components/selection/ProgressIndicator.tsx`:

```tsx
const STAGE_LABELS: Record<string, string> = {
  pending: '提交中',
  load_panel: '加载缓存面板',
  compute_indicators: '计算技术指标',
  score: '因子打分',
  filter_rank: '过滤 + Top-N 排序',
  done: '完成',
}

export function ProgressIndicator({
  stage,
  progress,
  message,
  slow,
}: {
  stage: string
  progress: number
  message: string
  slow: boolean
}) {
  const pct = Math.round(progress * 100)
  return (
    <div className="border border-border rounded-md bg-chart p-5 space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{STAGE_LABELS[stage] ?? stage}</span>
        <span className="text-ink-soft numeric">{pct}%</span>
      </div>
      <div className="h-1.5 bg-surface rounded-sm overflow-hidden">
        <div className="h-full bg-accent transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-ink-soft">{message}</div>
      {slow && (
        <div className="text-xs text-warn border-t border-border pt-2 mt-2">
          任务运行较慢,如长时间无响应可改用 CLI:<code className="font-mono">uv run quant-select candidates …</code>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/selection/ProgressIndicator.tsx
git commit -m "feat(web): ProgressIndicator with stage label + slow hint"
```

### Task D.4: SelectionResultsTable + CSV export

**Files:**
- Create: `web/lib/csv.ts`
- Create: `web/components/selection/SelectionResultsTable.tsx`

- [ ] **Step 1: Implement CSV helper**

Write `web/lib/csv.ts`:

```ts
export function downloadCsv(filename: string, rows: Record<string, unknown>[]): void {
  if (rows.length === 0) return
  const headers = Object.keys(rows[0])
  const escape = (v: unknown): string => {
    if (v == null) return ''
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const body = rows.map((r) => headers.map((h) => escape(r[h])).join(',')).join('\n')
  const csv = '﻿' + headers.join(',') + '\n' + body  // BOM for Excel zh-CN
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 2: Implement SelectionResultsTable**

Write `web/components/selection/SelectionResultsTable.tsx`:

```tsx
'use client'

import Link from 'next/link'
import type { SelectionResult } from '@/lib/api-types'
import { Button } from '@/components/ui/Button'
import { downloadCsv } from '@/lib/csv'

const FACTOR_LABELS: Record<string, string> = {
  ma_breakout: '均线突破',
  kdj_golden_cross: 'KDJ金叉',
  macd_golden_cross: 'MACD金叉',
  rsi_momentum: 'RSI动量',
  volume_breakout: '放量',
  boll_breakout: '布林突破',
}

export function SelectionResultsTable({ result }: { result: SelectionResult }) {
  const summary = result.summary as Record<string, number>
  const candidates = result.candidates

  const exportCsv = () => {
    downloadCsv(`选股_${result.as_of_date}.csv`, candidates.map((c, i) => ({
      序号: i + 1,
      标的: c.symbol,
      因子分: c.score,
      命中因子: c.factors_hit.join(';'),
      理由: c.reasons,
    })))
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="全市场" value={summary.total_universe} />
        <Stat label="过阈值" value={summary.passed_min_score} />
        <Stat label="Top-N" value={summary.top_n_returned} />
      </div>

      <div className="flex items-center justify-between">
        <div className="text-md font-medium">候选股({candidates.length})</div>
        <Button size="sm" variant="ghost" onClick={exportCsv}>导出 CSV</Button>
      </div>

      <div className="border border-border rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface text-ink-soft">
            <tr>
              <th className="text-right px-2 py-2 font-medium">#</th>
              <th className="text-left  px-2 py-2 font-medium">标的</th>
              <th className="text-right px-2 py-2 font-medium">因子分</th>
              <th className="text-left  px-2 py-2 font-medium">命中</th>
              <th className="text-left  px-2 py-2 font-medium">理由</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c, i) => (
              <tr key={c.symbol} className="border-t border-border hover:bg-accent-soft">
                <td className="px-2 py-1.5 numeric text-right text-ink-muted">{i + 1}</td>
                <td className="px-2 py-1.5">
                  <Link href={`/dashboard?symbol=${encodeURIComponent(c.symbol)}`} className="font-mono text-ink hover:underline">
                    {c.symbol}
                  </Link>
                </td>
                <td className="px-2 py-1.5 numeric text-right">{c.score}</td>
                <td className="px-2 py-1.5 space-x-1">
                  {c.factors_hit.map((f) => (
                    <span key={f} className="inline-block px-1.5 py-0.5 text-xs rounded-sm bg-accent-soft text-ink">
                      {FACTOR_LABELS[f] ?? f}
                    </span>
                  ))}
                </td>
                <td className="px-2 py-1.5 text-xs text-ink-soft truncate max-w-[280px]" title={c.reasons}>{c.reasons}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="border border-border rounded-md bg-chart p-3">
      <div className="text-xs text-ink-muted mb-1">{label}</div>
      <div className="text-lg numeric">{value.toLocaleString('en-US')}</div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add web/lib/csv.ts web/components/selection/SelectionResultsTable.tsx
git commit -m "feat(web): SelectionResultsTable with CSV export"
```

### Task D.5: Selection page wiring

**Files:**
- Modify: `web/app/selection/page.tsx`

- [ ] **Step 1: Implement**

Write `web/app/selection/page.tsx`:

```tsx
'use client'

import * as React from 'react'
import { useSubmitSelectionJob } from '@/lib/queries'
import { useSelectionJobStream } from '@/lib/sse'
import { useToast } from '@/components/ui/Toast'
import { FactorConfigPanel, type SelectionFormValues } from '@/components/selection/FactorConfigPanel'
import { ProgressIndicator } from '@/components/selection/ProgressIndicator'
import { SelectionResultsTable } from '@/components/selection/SelectionResultsTable'
import { ErrorBanner } from '@/components/feedback/ErrorBanner'
import { EmptyState } from '@/components/feedback/EmptyState'

export default function SelectionPage() {
  const [panelOpen, setPanelOpen] = React.useState(true)
  const [jobId, setJobId] = React.useState<string | null>(null)
  const [runStart, setRunStart] = React.useState<number | null>(null)
  const [slowNow, setSlowNow] = React.useState(false)
  const submit = useSubmitSelectionJob()
  const stream = useSelectionJobStream(jobId)
  const toast = useToast()

  React.useEffect(() => {
    if (stream.status !== 'running') { setSlowNow(false); return }
    if (runStart === null) return
    const id = setInterval(() => {
      setSlowNow(Date.now() - runStart > 15_000)
    }, 1_000)
    return () => clearInterval(id)
  }, [stream.status, runStart])

  const onSubmit = (values: SelectionFormValues) => {
    const body = {
      as_of_date: values.as_of_date || null,
      config: {
        min_score: values.min_score,
        top_n: values.top_n,
        exclude_suspended: values.exclude_suspended,
        exclude_st: values.exclude_st,
        require_factors: values.require_factors,
        exclude_factors: values.exclude_factors,
        ma_short: values.ma_short,
        ma_long: values.ma_long,
        rsi_window: values.rsi_window,
        rsi_threshold: values.rsi_threshold,
        volume_window: values.volume_window,
        volume_multiplier: values.volume_multiplier,
      },
      symbol_universe: null,
    }
    setRunStart(Date.now())
    submit.mutate(body, {
      onSuccess: ({ job_id }) => setJobId(job_id),
      onError: (err: Error) => toast.add({ tone: 'error', title: '提交失败', description: err.message }),
    })
  }

  const running = stream.status === 'running'

  return (
    <div className="flex" style={{ height: 'calc(100vh - 44px)' }}>
      {panelOpen && (
        <aside className="w-[320px] border-r border-border bg-canvas overflow-y-auto">
          <div className="px-4 pt-3 flex items-center justify-between">
            <div className="text-xs uppercase tracking-wide text-ink-muted">选股配置</div>
            <button
              onClick={() => setPanelOpen(false)}
              className="text-xs text-ink-soft hover:text-ink"
              aria-label="收起"
            >
              收起 ←
            </button>
          </div>
          <FactorConfigPanel onSubmit={onSubmit} disabled={running} />
        </aside>
      )}

      <div className="flex-1 overflow-y-auto">
        {!panelOpen && (
          <div className="px-5 pt-3">
            <button
              onClick={() => setPanelOpen(true)}
              className="text-xs text-ink-soft hover:text-ink"
              aria-label="展开"
            >
              → 展开配置
            </button>
          </div>
        )}

        <div className="p-5">
          {stream.status === 'idle' && (
            <EmptyState title="配置好因子后点开始选股" hint="左侧面板调整截止日期与因子参数,默认值适合一般情况。" />
          )}

          {stream.status === 'running' && (
            <ProgressIndicator
              stage={stream.stage}
              progress={stream.progress}
              message={stream.message}
              slow={slowNow}
            />
          )}

          {stream.status === 'done' && <SelectionResultsTable result={stream.result} />}

          {stream.status === 'failed' && <ErrorBanner>{stream.error}</ErrorBanner>}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Smoke test (full SSE round-trip)**

Backend running, at least one symbol's `qfq` cache present (e.g. `000001.SZ`). Open http://localhost:3000/selection.

Expected:
- Left panel shows config form filled with defaults
- Click 开始选股 → progress bar animates through 5 stages → results table appears
- Toggle 收起 ← / → 展开配置 → main area expands/shrinks accordingly
- Click 导出 CSV → browser downloads `选股_YYYY-MM-DD.csv`, opens cleanly in Excel (BOM)

- [ ] **Step 3: Commit**

```bash
git add web/app/selection/page.tsx
git commit -m "feat(web): selection page — config + SSE progress + results"
```

---

## Phase E — Sweep detail

### Task E.1: TopCombosCard

**Files:**
- Create: `web/components/reports/TopCombosCard.tsx`

- [ ] **Step 1: Implement**

Write `web/components/reports/TopCombosCard.tsx`:

```tsx
import { fmtPercent, fmtNumber } from '@/lib/format'

export function TopCombosCard({ combos, rankBy }: { combos: Record<string, unknown>[]; rankBy: string }) {
  if (!combos || combos.length === 0) return null
  return (
    <div className="border border-border rounded-md bg-chart p-4 space-y-2">
      <div className="text-md font-medium">Top {combos.length} 组合(按 {rankBy} 排序)</div>
      <ol className="space-y-1.5">
        {combos.map((c, i) => {
          const score = c[rankBy] as number | undefined
          const params = Object.entries(c).filter(([k]) => k !== 'combo_id' && k !== rankBy && !['total_return','sharpe','max_drawdown','win_rate','trades'].includes(k))
          return (
            <li key={String(c.combo_id ?? i)} className="text-sm flex items-baseline gap-3">
              <span className="text-ink-muted text-xs numeric w-5 text-right">{i + 1}.</span>
              <span className="numeric font-medium w-20 text-right">
                {rankBy.includes('return') || rankBy.includes('drawdown') ? fmtPercent(score) : fmtNumber(score)}
              </span>
              <span className="text-xs text-ink-soft truncate">
                {params.map(([k, v]) => `${k}=${v}`).join(' · ') || '—'}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/reports/TopCombosCard.tsx
git commit -m "feat(web): TopCombosCard summary"
```

### Task E.2: SweepResultsTable

**Files:**
- Create: `web/components/reports/SweepResultsTable.tsx`

- [ ] **Step 1: Implement**

Write `web/components/reports/SweepResultsTable.tsx`:

```tsx
'use client'

import * as React from 'react'
import { Button } from '@/components/ui/Button'
import { fmtNumber, fmtPercent } from '@/lib/format'

type Row = Record<string, unknown>
const METRIC_KEYS = new Set(['total_return', 'sharpe', 'max_drawdown', 'win_rate', 'trades', 'annual_return', 'annual_return_pct', 'max_drawdown_pct'])

function isPercent(key: string): boolean {
  return key.includes('return') && !key.endsWith('_pct') || key === 'max_drawdown' || key === 'win_rate'
}

function formatCell(key: string, value: unknown): string {
  if (value == null) return '—'
  if (typeof value !== 'number') return String(value)
  if (isPercent(key)) return fmtPercent(value)
  if (Number.isInteger(value)) return value.toLocaleString('en-US')
  return fmtNumber(value, 3)
}

export function SweepResultsTable({ rows, defaultSort }: { rows: Row[]; defaultSort: string }) {
  const columns = React.useMemo(() => {
    if (rows.length === 0) return []
    return Object.keys(rows[0])
  }, [rows])

  const [sortKey, setSortKey] = React.useState<string>(defaultSort)
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('desc')
  const [page, setPage] = React.useState(0)
  const PAGE = 25

  const sorted = React.useMemo(() => {
    const out = [...rows]
    out.sort((a, b) => {
      const va = a[sortKey]; const vb = b[sortKey]
      if (va == null) return 1
      if (vb == null) return -1
      const cmp = typeof va === 'number' && typeof vb === 'number'
        ? va - vb : String(va).localeCompare(String(vb))
      return sortDir === 'asc' ? cmp : -cmp
    })
    return out
  }, [rows, sortKey, sortDir])

  const pageRows = sorted.slice(page * PAGE, (page + 1) * PAGE)
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE))

  return (
    <div className="space-y-2">
      <div className="border border-border rounded-md overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-surface text-ink-soft">
            <tr>
              {columns.map((c) => {
                const isMetric = METRIC_KEYS.has(c)
                const active = sortKey === c
                return (
                  <th
                    key={c}
                    onClick={() => {
                      if (active) setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
                      else { setSortKey(c); setSortDir(isMetric ? 'desc' : 'asc') }
                    }}
                    className={`px-2.5 py-2 cursor-pointer font-medium select-none whitespace-nowrap ${isMetric ? 'text-right' : 'text-left'}`}
                  >
                    {c}{active && (sortDir === 'asc' ? ' ▲' : ' ▼')}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((r, i) => (
              <tr key={String(r.combo_id ?? i)} className="border-t border-border hover:bg-accent-soft">
                {columns.map((c) => (
                  <td key={c} className={`px-2.5 py-1.5 numeric ${METRIC_KEYS.has(c) ? 'text-right' : 'text-left'}`}>
                    {formatCell(c, r[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-xs text-ink-soft">
        <span>共 {sorted.length} 个组合</span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>上一页</Button>
          <span>{page + 1} / {totalPages}</span>
          <Button size="sm" variant="ghost" disabled={page >= totalPages - 1} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}>下一页</Button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/reports/SweepResultsTable.tsx
git commit -m "feat(web): SweepResultsTable — dynamic columns sortable"
```

### Task E.3: Wire sweep branch in report detail

**Files:**
- Modify: `web/app/reports/[runId]/page.tsx`

- [ ] **Step 1: Replace sweep placeholder**

In `web/app/reports/[runId]/page.tsx`, replace the `SweepBranchPlaceholder` reference and definition with a real implementation. Replace:

```tsx
function SweepBranchPlaceholder() {
  return <div className="text-ink-soft text-sm">(Sweep 详情见 Milestone E)</div>
}
```

with:

```tsx
function SweepBranch({ runId, manifest }: { runId: string; manifest: Record<string, unknown> }) {
  const sweep = useReportSweep(runId)
  const rankBy = (manifest.rank_by as string) ?? 'total_return'
  const topCombos = (manifest.top_combos as Record<string, unknown>[]) ?? []
  return (
    <>
      <div className="text-md text-ink-soft">
        策略:{String(manifest.strategy ?? '—')} · rank_by:{rankBy} · grid_size:{String(manifest.grid_size ?? '—')}
      </div>
      <TopCombosCard combos={topCombos} rankBy={rankBy} />
      <div>
        <div className="text-md font-medium mb-2">全部组合</div>
        {sweep.isLoading ? <Skeleton className="h-40 w-full" /> :
          sweep.data ? <SweepResultsTable rows={sweep.data.rows as Record<string, unknown>[]} defaultSort={rankBy} /> :
          null}
      </div>
    </>
  )
}
```

Update the call site in `ReportDetailPage` from `<SweepBranchPlaceholder />` to:

```tsx
{kind === 'sweep' ? <SweepBranch runId={runId} manifest={m} /> : null}
```

Add the needed imports at the top of the file:

```tsx
import { TopCombosCard } from '@/components/reports/TopCombosCard'
import { SweepResultsTable } from '@/components/reports/SweepResultsTable'
```

- [ ] **Step 2: Smoke test**

Run `uv run quant-backtest sweep --symbols 000001.SZ --strategy sma-cross --fast-periods 5,10 --slow-periods 20,30` to produce a sweep report (or use any existing one). Visit it through `/reports`.

Expected:
- Title row shows strategy / rank_by / grid_size
- TopCombosCard lists the top 5
- Below: the full sweep table renders with all dynamic param columns, sortable
- 元信息 panel collapses cleanly

- [ ] **Step 3: Commit**

```bash
git add web/app/reports/[runId]/page.tsx
git commit -m "feat(web): wire sweep branch into report detail"
```

---

## Phase F — Polish + docs

### Task F.1: README updates

**Files:**
- Modify: `README.md`
- Modify: `README-CN.md`
- Create: `web/README.md`

- [ ] **Step 1: Append "Run the frontend" to root README.md**

Append the following section after the existing "Run the read-only API" section in `README.md`:

```markdown
## Run the web frontend

The frontend lives in `web/` and is a Next.js 15 App Router single-page app.

Install once:

```bash
cd web
npm install
```

Run both backend and frontend:

```bash
# Terminal 1 (from repo root)
uv run quant-api

# Terminal 2 (from repo root)
cd web && npm run dev
```

Open http://localhost:3000. The frontend reverse-proxies `/api/*` to the
FastAPI backend at `http://127.0.0.1:8000`. Three pages — dashboard,
selection, reports — render data from the cache and the `reports/`
directory produced by `quant-backtest sweep` / `validate`.

Regenerate API types after any backend schema change:

```bash
cd web && npm run gen:api
```
```

- [ ] **Step 2: Append 中文 section to README-CN.md**

After the existing "启动只读 API" section, append:

```markdown
### 启动 Web 前端

前端位于 `web/`,Next.js 15 App Router 单页应用。

首次安装:

```bash
cd web
npm install
```

同时启动后端和前端:

```bash
# 终端 1(仓库根)
uv run quant-api

# 终端 2(仓库根)
cd web && npm run dev
```

浏览器打开 http://localhost:3000。前端通过 Next.js rewrites 把 `/api/*`
反代到 `http://127.0.0.1:8000`。三个页面分别是看板、选股、报告。

后端 schema 变更后重新生成前端类型:

```bash
cd web && npm run gen:api
```
```

- [ ] **Step 3: Write web/README.md**

Write `web/README.md`:

```markdown
# Muce Web Frontend

Next.js 15 + TypeScript + Tailwind. Sits on top of the FastAPI backend
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
- `lib/api-types.ts` — thin domain types
- `styles/tokens.css` — color, font, radius, spacing variables

## Conventions

- All page components are `'use client'`. No RSC.
- URL search params are the source of truth for filters; React state for
  local UI only; localStorage for cross-session preferences (not used in
  v1).
- Charts use `lightweight-charts`. Future heatmaps will use ECharts.
- Errors flow: network → `ApiError` → TanStack Query `error` → row-inline
  `<ErrorBanner>` or `<Toast>` (mutations).
```

- [ ] **Step 4: Commit**

```bash
git add README.md README-CN.md web/README.md
git commit -m "docs: how to run the frontend"
```

### Task F.2: Devlog + ADR + docs/README

**Files:**
- Create: `docs/devlog/2026-05-11-web-frontend.md`
- Create: `docs/devlog/records/ADR-011_2026-05-11_web-frontend-stack.md`
- Modify: `docs/devlog/records/README.md`
- Modify: `docs/devlog/CHANGELOG.md`
- Modify: `docs/devlog/current/capabilities.md`
- Modify: `docs/devlog/current/overview.md`
- Modify: `docs/README.md`

- [ ] **Step 1: Write devlog**

Write `docs/devlog/2026-05-11-web-frontend.md`:

```markdown
# Web Frontend v1

**Date:** 2026-05-11
**Spec:** [docs/superpowers/specs/2026-05-11-web-frontend-design.md](../superpowers/specs/2026-05-11-web-frontend-design.md)
**Plan:** [docs/superpowers/plans/2026-05-11-web-frontend.md](../superpowers/plans/2026-05-11-web-frontend.md)
**ADR:** [docs/devlog/records/ADR-011_2026-05-11_web-frontend-stack.md](records/ADR-011_2026-05-11_web-frontend-stack.md)

## Summary

Built a Next.js 15 + TypeScript single-page web frontend over the FastAPI
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

## Key decisions

- **Next.js (App Router) + all client components**, no RSC. Local-only tool,
  no SEO / edge-rendering payoff.
- **Reverse-proxy `/api/*` through Next.js** to avoid CORS in the browser
  path; backend CORS remains as a fallback for direct connections.
- **TanStack Query v5 + `openapi-typescript`** for data + type sync. Single
  generated types file, thin domain layer, retry policy 4xx-no / 5xx-twice.
- **`lightweight-charts` for K-line and equity** (TradingView library used by
  FinGOAT). ECharts deferred to v2 for sweep heatmaps.
- **SSE only for selection progress.** Daemon thread on the backend, a
  custom `useSelectionJobStream` hook on the frontend, closes on
  `done` / `failed` / unmount.
- **Tailwind + CSS variables**, no UI library. FinGOAT palette adapted:
  more restrained, single olive accent, A-share convention 红涨绿跌.
- **TopBar 44px, Toolbar 52px, chart stage full-bleed no radius.** Main
  area dominates; chrome stays out of the way.

## What changed

- New `web/` subdirectory: 60+ files across `app/`, `components/`, `lib/`,
  `styles/`, `tests/`.
- Root `.gitignore`: ignore `web/node_modules/`, `.next/`, `out/`,
  `coverage/`.
- New docs: this devlog, ADR-011, plan, spec.

## Verification

- `cd web && npm test` — Vitest suite green (format / url-state / api /
  sse).
- `cd web && npx tsc --noEmit` — TS clean.
- Manual smoke: backend running, browse all three pages including a full
  selection round-trip, validate report, and sweep report.

## Follow-ups (out of scope for v1)

- Sweep heatmap (ECharts).
- Dark mode (`:root.theme-dark` hook exists, no styles).
- Mobile responsive (current breakpoint floor ≈ 1280px).
- Job persistence (currently in-process registry).
- More indicators on K-line (KDJ / MACD / Bollinger).
```

- [ ] **Step 2: Write ADR**

Write `docs/devlog/records/ADR-011_2026-05-11_web-frontend-stack.md`:

```markdown
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

1. **Next.js 15 App Router + TypeScript strict** in `web/`. All pages are
   client components; no RSC / SSR.
2. **Reverse-proxy `/api/*` to `http://127.0.0.1:8000`** via
   `next.config.mjs` rewrites. Avoids browser CORS path.
3. **Tailwind CSS 4 + custom CSS variables** for design tokens. No UI
   library; Radix primitives only for interactive controls (Select,
   Popover, Dialog, Tooltip, Toast, Checkbox, Collapsible).
4. **Visual style references FinGOAT**: tactile warm palette,
   `--radius-sm/md/lg = 4/6/8px`, full-bleed `chart-stage` with no radius
   or border, single olive accent. A-share convention 红涨绿跌.
5. **TanStack Query v5** for data fetching. queryKey factories in
   `lib/queries.ts`. Retry: 4xx never, 5xx twice.
6. **`openapi-typescript`** generates `lib/api-generated.ts` from FastAPI's
   `/openapi.json`. Thin domain types in `lib/api-types.ts` shield business
   code from generator quirks.
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

- One generated types file binds frontend tightly to backend; schema drift
  becomes a compile error.
- Reverse-proxy hides API origin from frontend code; deployment-day config
  changes don't touch components.
- Tailwind + CSS variables means design tokens can be edited in one file
  without touching components.
- `lightweight-charts` is the same library FinGOAT uses; transfer of
  patterns is direct.

**Accepted negatives**

- Next.js with all-client pages is overkill compared to Vite. Mitigation:
  almost no Next.js features beyond `app/` routing + rewrites are used; can
  migrate to Vite later without breaking the directory layout.
- No UI library means each interactive primitive (Combobox, Toast, Dialog)
  is implemented locally. Mitigation: Radix primitives carry the
  accessibility weight; thin wrappers are < 50 lines each.
- TanStack Query in client-only mode loses some RSC integration benefits.
  Acceptable — not used.

## Notes

- The plan's milestone breakdown produced 60+ files across 6 phases; see
  the plan for the full structure.
- Future ADRs may revisit:
  - ECharts adoption (sweep heatmap, factor attribution radar).
  - Migration to Vite if Next.js features remain unused at v2.
```

- [ ] **Step 3: Index in records README**

In `docs/devlog/records/README.md`, after the ADR-010 row, append:

```
| [ADR-011](ADR-011_2026-05-11_web-frontend-stack.md) | 2026-05-11 | Web Frontend Stack — Next.js + TanStack Query + lightweight-charts | decision | accepted |
```

- [ ] **Step 4: Append CHANGELOG entry**

In `docs/devlog/CHANGELOG.md`, under `Unreleased (v0.1.0-dev)` add a new dated entry above the existing 2026-05-10 entry:

```markdown
### 2026-05-11 — Web Frontend (v1)
- Next.js 15 App Router + TypeScript app under `web/`
- Three pages: 标的看板 / 选股(含 SSE 进度) / 回测报告
- TanStack Query v5 + openapi-typescript for type-safe API client
- lightweight-charts for K-line and equity curve
- Tailwind + CSS variables; FinGOAT-derived palette (低圆角、单一强调色、A股红涨绿跌)
- Vitest unit tests for format / url-state / api / sse
```

- [ ] **Step 5: Update capabilities.md**

Append a new top-level section to `docs/devlog/current/capabilities.md`:

```markdown

## Web Frontend

- Next.js 15 App Router single-page app in `web/`
- Three pages: dashboard (K-line + indicators + last-10 OHLC), selection (factor config + SSE progress + candidates with CSV export), reports (list + validate detail / sweep detail)
- TanStack Query v5 for data fetching with retry policy (4xx never, 5xx twice)
- openapi-typescript auto-generates types from backend OpenAPI
- lightweight-charts for K-line and equity; ECharts deferred to v2
- Reverse-proxy `/api/*` to FastAPI backend
- Vitest unit suite for lib helpers and SSE hook state machine
```

- [ ] **Step 6: Update overview.md**

In `docs/devlog/current/overview.md`, append to the "What Works" list:

```markdown
- Next.js web frontend (`web/`) with three pages: dashboard, selection, reports
```

- [ ] **Step 7: Update docs/README.md**

In `docs/README.md`, under `### Records`, after the ADR-010 line, add:

```markdown
- [ADR-011: Web Frontend Stack](devlog/records/ADR-011_2026-05-11_web-frontend-stack.md)
```

Under `### Design`, after the FastAPI plan line, add:

```markdown
- [Spec: Web Frontend (v1)](superpowers/specs/2026-05-11-web-frontend-design.md)
- [Plan: Web Frontend (v1)](superpowers/plans/2026-05-11-web-frontend.md)
```

Add a new entry under the existing devlog list:

```markdown
- [Web Frontend (v1)](devlog/2026-05-11-web-frontend.md)
```

If `docs/README.md` doesn't have an explicit devlog list section, append the entry near the existing devlog references.

- [ ] **Step 8: Commit**

```bash
git add docs/devlog/2026-05-11-web-frontend.md docs/devlog/records/ADR-011_2026-05-11_web-frontend-stack.md docs/devlog/records/README.md docs/devlog/CHANGELOG.md docs/devlog/current/capabilities.md docs/devlog/current/overview.md docs/README.md
git commit -m "docs: devlog, ADR-011, capabilities, overview for web frontend"
```

### Task F.3: Final regression sweep

- [ ] **Step 1: Run full test suite**

```bash
cd web && npm test
```

Expected: all PASS.

- [ ] **Step 2: TypeScript clean**

```bash
cd web && npx tsc --noEmit
```

Expected: no output.

- [ ] **Step 3: Build production bundle**

```bash
cd web && npm run build
```

Expected: build succeeds with no errors. (Warnings about missing favicon are fine.)

- [ ] **Step 4: Backend still green**

From repo root:

```bash
uv run pytest tests/ -q
```

Expected: same pass count as before this work (107 passed, 3 skipped, give or take environment skips).

- [ ] **Step 5: Manual smoke walkthrough**

Backend running. Open http://localhost:3000.

Check each:
- [ ] `/dashboard`: select 000001.SZ, toggle qfq/raw, toggle ma_20 / ma_60 / rsi_14 indicators, see K-line update, see right sidebar with info + last 10 OHLC
- [ ] `/selection`: submit a small selection (`min_score=0, top_n=10`), watch progress bar through stages, see candidates table, click a symbol to jump to dashboard, click 导出 CSV → verify the downloaded file opens in Excel with 中文 columns visible
- [ ] `/reports`: click a validate report → equity curve, trades table, expand 元信息 panel
- [ ] `/reports`: click a sweep report → top combos card, full sweep table sortable
- [ ] Kill `quant-api` (Ctrl-C in its terminal) → frontend TopBar HealthBadge turns to "后端离线" → error boundary shows on next data refetch with a 重试 button

- [ ] **Step 6: No commit unless cleanup happened**

If the smoke surfaced fixable issues, commit them per task style. Otherwise this task is verification-only.

---

## Self-Review Notes

**Spec coverage**

| Spec section | Plan task(s) |
|---|---|
| §1 Background / Non-goals | Captured in plan header + Task F.2 devlog/ADR |
| §2 Tech stack | Tasks A.1–A.7 install + config |
| §3 Project structure | Tasks A.1 / A.3 / A.5 / A.6 |
| §4 Design system (tokens, layout grid) | Tasks A.5 / A.6 / A.11 |
| §5.1 Dashboard | Phase B (Tasks B.1–B.8) |
| §5.2 Selection | Phase D (Tasks D.1–D.5) |
| §5.3 Reports list | Task C.1–C.2 |
| §5.4 Report detail validate | Task C.3–C.7 |
| §5.4.2 Report detail sweep | Phase E (Tasks E.1–E.3) |
| §6 SSE design | Task D.1 + D.5 |
| §7 Backend integration (types, http, queries, errors) | Tasks A.8–A.10 + Task A.9's `ApiError` tests |
| §8 Milestones | Phases A–F mirror milestones A–F |
| §9 Testing strategy | Tasks A.7 / A.9 / A.12 / A.13 / D.1 |
| §10 Risks | Addressed in plan via TS strict gen step (A.8), per-page error boundaries (A.14), slow-job indicator (D.3 + D.5), HealthBadge offline (A.11), StrictMode chart cleanup (B.6 / C.5) |

**Type consistency check**: `BarRow`, `SelectionResult`, `JobUIState`, `ReportManifest`, `Stat`, `BarsOpts`, `ApiError` introduced in earlier tasks and reused with identical field names through later tasks.

**Placeholder scan**: No "TBD" / "implement later" / unresolved references found. The plan references `<ApiError>` only after defining it in A.9; `useReportSweep` is defined in A.10 and used in E.3; `MetaPanel`, `TopCombosCard`, `SweepResultsTable` are all defined before being imported in `/reports/[runId]/page.tsx`.
