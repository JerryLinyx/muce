# Web Frontend Design (v1)

**日期**:2026-05-11
**状态**:设计已批准,待生成实施计划
**作者**:brainstorming session (Yuxuan + Claude)
**前置**:[2026-05-10-fastapi-readonly-backend-design.md](./2026-05-10-fastapi-readonly-backend-design.md)

---

## 1. 背景与目标

后端 FastAPI 只读 API 已上线(16 个 endpoint,4 个 router)。本 spec 设计前端 v1:**Next.js + TypeScript 单页应用**,呈现三个核心页面——**标的看板 / 选股 / 回测报告**——构成 A 股研究终端。

### 视觉与体验目标

- **沉浸式**:主体图表 / 表格占满可用空间,TopBar / Toolbar 收到 44/52px,主图区 full-bleed 无圆角
- **克制**:圆角 ≤ 8px,无戏剧化阴影 / 渐变 / blur;单一强调色(muted olive);A 股惯例红涨绿跌
- **中文优先**:文案全中文,无 i18n 切换;字体 Inter + PingFang/YaHei 回退
- **键盘友好**:K 线支持平移/缩放/全屏;表格支持点击排序

### 非目标(v1 明确不做)

- ❌ 移动端响应式(< 1280px 不保证可用)
- ❌ 深色模式(预留 `.theme-dark` hook 但不实现样式)
- ❌ i18n 切换
- ❌ 用户 / 鉴权
- ❌ SSR / RSC(全 client component)
- ❌ Sweep 热图(v2 用 ECharts 加)
- ❌ K 线分钟级
- ❌ 多窗口状态同步
- ❌ PWA / 离线
- ❌ 导出 PDF / Excel(v1 只 CSV)

---

## 2. 技术栈

| 类别 | 选择 |
|---|---|
| 框架 | Next.js 15+ App Router |
| 语言 | TypeScript(strict 模式) |
| 样式 | Tailwind CSS 4 + 自定义 CSS 变量(色板从 [FinGOAT](~/workSpace/FinGOAT) 借) |
| 字体 | Inter(`next/font/google`)+ PingFang SC / Microsoft YaHei 回退 |
| K 线 / 时序图 | `lightweight-charts` v5(TradingView 出品) |
| 其他图表(v2) | `echarts` + `echarts-for-react` |
| 交互原语 | `@radix-ui/react-*`(Select / Dialog / Popover / Tooltip / Toast) |
| 数据获取 | TanStack Query v5 |
| SSE | 原生 `EventSource`,封装成 `useSelectionJobStream` hook |
| 表单 | `react-hook-form` + `zod` |
| 日期 | `dayjs` + `dayjs/locale/zh-cn` |
| 状态管理 | URL search params(filter)+ React state(本地)+ localStorage(用户偏好);**不引入 Zustand** |
| 路由 | Next.js App Router file-based |
| 类型同步 | `openapi-typescript` 从 `/openapi.json` 生成 |

---

## 3. 项目结构

### 目录布局

```
muce/
├── src/quant_backtest/          # Python 后端(已存在)
├── web/                          # 新增:Next.js 前端
│   ├── app/
│   │   ├── layout.tsx            # 全局壳:TopBar + Providers
│   │   ├── page.tsx              # / → redirect /dashboard
│   │   ├── globals.css           # tokens + 全局 + Tailwind import
│   │   ├── error.tsx             # 全局 ErrorBoundary
│   │   ├── dashboard/
│   │   │   ├── page.tsx          # ① 标的看板
│   │   │   └── error.tsx
│   │   ├── selection/
│   │   │   ├── page.tsx          # ② 选股
│   │   │   └── error.tsx
│   │   └── reports/
│   │       ├── page.tsx          # ③ 报告列表
│   │       ├── error.tsx
│   │       └── [runId]/
│   │           ├── page.tsx      # ③' 单份报告详情
│   │           └── error.tsx
│   ├── components/
│   │   ├── ui/                   # 基础原语(Button / Select / Dialog / Toast)
│   │   ├── chart/
│   │   │   ├── KLineChart.tsx
│   │   │   └── EquityChart.tsx
│   │   ├── selection/
│   │   │   ├── FactorConfigPanel.tsx
│   │   │   ├── SelectionResultsTable.tsx
│   │   │   └── ProgressIndicator.tsx
│   │   ├── reports/
│   │   │   ├── ReportListTable.tsx
│   │   │   ├── SweepResultsTable.tsx
│   │   │   ├── TradesTable.tsx
│   │   │   └── StatGrid.tsx
│   │   ├── topbar/
│   │   │   └── TopBar.tsx
│   │   └── feedback/
│   │       ├── ErrorBanner.tsx
│   │       ├── EmptyState.tsx
│   │       └── Skeleton.tsx
│   ├── lib/
│   │   ├── api.ts                # fetcher + 每 endpoint 一个函数
│   │   ├── api-generated.ts      # 自动生成,勿手改
│   │   ├── api-types.ts          # thin domain types,从 generated 派生
│   │   ├── queries.ts            # queryKey 工厂 + Query/Mutation hooks
│   │   ├── query-client.ts       # QueryClient 单例 + 重试策略
│   │   ├── sse.ts                # useSelectionJobStream hook
│   │   ├── format.ts             # 中文千分位 / 百分比 / 日期
│   │   ├── url-state.ts          # URL search params <-> typed state
│   │   └── csv.ts                # 客户端 CSV 导出
│   ├── styles/
│   │   └── tokens.css            # 色板 / 字号 / 间距 / 圆角 token
│   ├── public/                   # favicon
│   ├── next.config.mjs           # rewrites: /api/* → http://127.0.0.1:8000/api/*
│   ├── tailwind.config.ts        # 接入 CSS 变量
│   ├── tsconfig.json
│   ├── postcss.config.mjs
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── README.md
├── .gitignore                    # 追加 web/node_modules/ web/.next/ web/out/
└── README.md / README-CN.md      # 主仓库 README 加"前端开发"段落
```

### `next.config.mjs` 关键配置

```js
const config = {
  async rewrites() {
    return [
      { source: '/api/:path*', destination: 'http://127.0.0.1:8000/api/:path*' },
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
```

反代后端 → 浏览器一律走 `/api/*` 同源相对路径,**绕过 CORS**(后端 CORS 配置仍存在,作为绕开 Next.js 直连后端时的兜底)。

### `.gitignore` 追加

```
web/node_modules/
web/.next/
web/out/
web/pnpm-debug.log
```

---

## 4. 设计系统

### 4.1 色板(CSS 变量)

```css
:root {
  /* 中性色 */
  --ink-black:      #1a1a14;
  --ink-soft:       #5c5c56;
  --ink-muted:      #8b8a85;

  --canvas:         #f3f1ed;
  --panel:          #ecebea;
  --panel-strong:   #e0d6c5;
  --surface-soft:   #e5e3db;

  /* 图表区域(更亮,做"沉入") */
  --chart-bg:       #fbfaf6;
  --chart-grid:     rgba(26, 26, 20, 0.06);
  --chart-axis:     rgba(26, 26, 20, 0.35);

  /* 边框 / 阴影(极克制) */
  --border:         rgba(26, 26, 20, 0.08);
  --border-strong:  rgba(26, 26, 20, 0.16);
  --shadow-sm:      0 1px 2px rgba(26, 26, 20, 0.04);
  --shadow-md:      0 4px 12px rgba(26, 26, 20, 0.06);

  /* 涨跌色:A 股惯例红涨绿跌 */
  --up:             #c14747;
  --up-soft:        rgba(193, 71, 71, 0.12);
  --down:           #4a7d52;
  --down-soft:      rgba(74, 125, 82, 0.12);

  /* 单一强调色 */
  --accent:         #6b7c5e;
  --accent-soft:    rgba(107, 124, 94, 0.14);

  --warn:           #c08a3a;
  --error:          #cc4b4b;
}
```

### 4.2 字号 / 字重

```css
:root {
  --font-sans: 'Inter', -apple-system, system-ui, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-mono: ui-monospace, 'JetBrains Mono', 'SF Mono', Menlo, monospace;

  --fs-xs:    12px;
  --fs-sm:    13px;
  --fs-base:  14px;
  --fs-md:    15px;
  --fs-lg:    18px;
  --fs-stat:  22px;

  --fw-regular: 400;
  --fw-medium:  500;
  --fw-semibold: 600;
}

.numeric { font-variant-numeric: tabular-nums; font-family: var(--font-mono); }
```

### 4.3 圆角 / 间距

```css
:root {
  --radius-sm: 4px;   /* button / input / badge */
  --radius-md: 6px;   /* card / panel / dropdown */
  --radius-lg: 8px;   /* dialog 最大值 */
  /* 无 --radius-xl,无 999px pill */

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
}
```

**主图区**特殊处理:

```css
.chart-stage {
  border-radius: 0;
  border: none;
  background: var(--chart-bg);
  padding: 0;
  min-height: 480px;
  flex: 1;
}
```

### 4.4 布局栅格

```
┌─ TopBar (44px, 固定) ────────────────────────────────────────┐
│  Muce · 看板 | 选股 | 报告                              [⚙]  │
├──────────────────────────────────────────────────────────────┤
│ Toolbar (52px, sticky, 浅描边底)                              │
│   页面专属控件(标的选择 / 因子配置 / 报告过滤器)            │
├──────────────────────────────────────────────────────────────┤
│ Main(剩余空间,full-bleed,沉浸区)                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. 页面规范

### 5.1 `/dashboard` — 标的看板

**布局**:Toolbar(SymbolSelector / Adjust / DateRange / Indicators 复选)+ Main(K 线主图 + 侧栏标的信息 / 最近 OHLC 表)。

**数据**:

| 区块 | Hook | Endpoint |
|---|---|---|
| Symbol 下拉 | `useSymbols({ q, market })` | `GET /api/symbols?q&market&limit=50` |
| 标的基本信息 | `useSymbolInfo(symbol)` | `GET /api/symbols/{symbol}` |
| K 线 + 指标 | `useBars(symbol, { adjust, start, end, indicators })` | `GET /api/bars/{symbol}?adjust&indicators=ma_20,ma_60,rsi_14` |

**交互**:
- URL 即状态:`/dashboard?symbol=000001.SZ&adjust=qfq&start=...&end=...&indicators=ma_20,rsi_14`
- 标的输入 debounce 300ms
- K 线区按 `F` 键全屏(`requestFullscreen` API)
- 加载:K 线区灰色脉冲;表格 `<TableSkeleton rows={10} />`
- 空缓存:K 线区显示"该标的尚未下载,请运行 `quant-data download --symbols ...`"
- 错误:Toast 显示 `error.message`

### 5.2 `/selection` — 选股

**布局**:左 `FactorConfigPanel`(默认 320px,可一键收起)+ 右 `ResultArea`(状态驱动)。

**配置面板字段**:
- 截止日期(DatePicker)
- 6 个因子启用(toggle group,中文 label 来自 `/api/selection/factors`)
- 排序参数:`min_score` / `top_n`
- 过滤:`exclude_suspended` / `exclude_st` / `require_factors` / `exclude_factors`
- 调参(折叠默认隐藏):`FactorSelectorConfig` 全部 dataclass 字段

**数据 & 状态机**:

| 区块 | Hook |
|---|---|
| 因子元数据 | `useFactors()`(`staleTime: Infinity`) |
| 默认配置 | `useSelectionDefaults()`(`staleTime: Infinity`) |
| 提交 | `useSubmitSelectionJob()` mutation |
| 进度流 | `useSelectionJobStream(jobId)` SSE |

**状态**:`idle → running(进度条) → done(候选股表) | failed(错误)`。运行超过 15s 时 UI 显示"任务运行较慢,可改用 CLI"提示。

**结果表列**:序号 / 标的(点击跳 `/dashboard?symbol=...`)/ 因子分 / 命中因子 badge / 理由(tooltip 显示完整)+ 顶部 Summary 三个 stat(total_universe / passed_min_score / top_n_returned)。

**导出**:候选表"导出 CSV"按钮,文件名 `选股_{as_of_date}.csv`。

### 5.3 `/reports` — 报告列表

**布局**:Toolbar(kind 切换 / since 输入 / 刷新)+ ReportListTable。

**数据**:`useReports({ kind, since })` → `GET /api/reports`。

**列**:run_id 简写 / 类型 / 策略 / 标的数 / 用时 / created_at / 操作(详情链接)。

**排序**:默认 `created_at` 降序;支持点列头排序。

### 5.4 `/reports/[runId]` — 报告详情

**根据 manifest.kind 分支**。

#### 5.4.1 `kind = "validate"`

```
[< 返回]  策略 · 信号/执行调整  · 用时
─────────────────────────────────────────
StatGrid:总收益 / 夏普 / 最大回撤 / 交易数
─────────────────────────────────────────
EquityChart:lightweight-charts
  - LineSeries: equity
  - AreaSeries: drawdown(红填充)
  - markers: 买卖标记(从 trades 派生)
─────────────────────────────────────────
TradesTable:sortable, paginate 20/页
  trade_id / 标的 / 方向 / 开仓 / 平仓 / size / 盈亏 / 收益率
─────────────────────────────────────────
元信息(Collapsible):run_id / git_commit / git_dirty
  / 数据区间 / 完整 config(JSON 折叠面板)
```

**数据**:`useReportDetail(runId)` + `useReportEquity(runId)` + `useReportTrades(runId)`。

**导出**:交易明细表"导出 CSV"按钮。

#### 5.4.2 `kind = "sweep"`

```
[< 返回]  策略 · rank_by · 用时
─────────────────────────────────────────
Summary:grid_size · top combo 一句话快报
─────────────────────────────────────────
TopCombosCard:前 5 名组合卡片(从 manifest.top_combos 直读)
─────────────────────────────────────────
SweepResultsTable:全表 sortable, paginate
  combo_id / <动态参数列> / total_return / sharpe / max_drawdown / ...
─────────────────────────────────────────
元信息(折叠)
```

**数据**:`useReportDetail(runId)` + `useReportSweep(runId)`。

**v1 不画热图**——v2 才引入 ECharts。

---

## 6. SSE 设计

### 6.1 仅用于选股进度

其他场景全部走 TanStack Query 普通 GET。SSE 只用于:
```
POST /api/selection/jobs → 拿 {job_id}
GET  /api/selection/jobs/{id}/stream → progress / done / failed 事件流
```

### 6.2 `useSelectionJobStream` hook(放 `lib/sse.ts`)

```typescript
type JobState =
  | { status: 'idle' }
  | { status: 'running'; stage: string; progress: number; message: string }
  | { status: 'done'; result: SelectionResult }
  | { status: 'failed'; error: string }

export function useSelectionJobStream(jobId: string | null): JobState {
  const [state, setState] = useState<JobState>({ status: 'idle' })

  useEffect(() => {
    if (!jobId) return
    setState({ status: 'running', stage: 'pending', progress: 0, message: '提交中...' })

    const es = new EventSource(`/api/selection/jobs/${jobId}/stream`)

    es.addEventListener('progress', (e) => {
      const p = JSON.parse((e as MessageEvent).data)
      setState({ status: 'running', stage: p.stage, progress: p.progress, message: p.message })
    })
    es.addEventListener('done', (e) => {
      const p = JSON.parse((e as MessageEvent).data)
      setState({ status: 'done', result: p.result })
      es.close()
    })
    es.addEventListener('failed', (e) => {
      const p = JSON.parse((e as MessageEvent).data)
      setState({ status: 'failed', error: p.error })
      es.close()
    })
    es.onerror = () => {
      /* EventSource 自带重连;v1 不显式 polling fallback */
    }

    return () => es.close()
  }, [jobId])

  return state
}
```

**工程细节**:
- `next.config.mjs` 加 `X-Accel-Buffering: no` 头确保不被缓冲
- `jobId` 切换或卸载时 cleanup 一定关流(EventSource 实例不能泄漏)
- 失败事件 / 卸载都会 `es.close()`

---

## 7. 后端联调约定

### 7.1 类型自动生成

```bash
# package.json
"scripts": {
  "gen:api": "openapi-typescript http://127.0.0.1:8000/openapi.json -o lib/api-generated.ts"
}
```

业务代码引用 `lib/api-types.ts`(thin domain 层),`api-types.ts` 从 `api-generated.ts` 派生。后端 schema 改了 → 跑 `pnpm gen:api` → 编译失败定位破坏点。

### 7.2 网络层

`lib/api.ts` 提供单一 `http<T>` fetcher:
- 自动解 envelope(业务代码拿 `data`,不要 `.data`)
- 自动抛 `ApiError`(`code` / `message` / `status` / `details`),解析 RFC 7807 错误体
- 16 个 endpoint 各包一个函数,集中在 `export const api = { ... }`

### 7.3 TanStack Query 模式

- `queryKey` 工厂集中在 `lib/queries.ts`,**每个 endpoint 一个**
- `staleTime` 策略:

| 数据 | staleTime |
|---|---|
| factors / defaults | `Infinity`(后端常量) |
| bars / symbols / coverage | 5 分钟 |
| reports 列表 | 30 秒 |
| report 详情 / artifacts | `Infinity`(产物不可变) |
| job 状态(轮询) | 0 |

- 重试:4xx 不重试,5xx 重试 2 次

### 7.4 错误三档

1. **网络层**:`http<T>` 抛 `ApiError`
2. **Query 层**:TanStack Query `retry` 策略 + `error` 状态
3. **UI**:
   - 查询失败:行内 `<ErrorBanner>` / 表格"加载失败"行
   - 提交失败(mutation):右下角 Toast 4 秒
   - 全局兜底:`error.tsx`(App Router)

---

## 8. 实施阶段

每个 milestone 完成后**前端就能跑起来给人看**。

### Milestone A — 骨架(~0.5 天)

可见结果:`pnpm dev` 启动,三个空页面可切换,TopBar 角标显示后端 `/api/health`。

- 初始化 `web/`:`pnpm create next-app`(App Router + TS + Tailwind)
- 安装依赖:`@tanstack/react-query` `@tanstack/react-query-devtools` `@radix-ui/react-*` `lightweight-charts` `react-hook-form` `zod` `dayjs` `openapi-typescript`
- `next.config.mjs` rewrites + SSE headers
- `globals.css` + `styles/tokens.css`:加载字体 / 注入 CSS 变量
- `tailwind.config.ts` 接入 CSS 变量
- `lib/api.ts` + `lib/queries.ts` + `lib/query-client.ts` 骨架
- `app/layout.tsx`:Providers + TopBar + 三个 tab
- `app/{dashboard,selection,reports}/page.tsx`:空壳
- `pnpm gen:api` 跑通

### Milestone B — 看板 MVP(~1 天)

可见结果:选标的 → K 线 + 指标叠加 + 最近 10 日表格。

- `SymbolSelector`(Radix Combobox + debounce + `useSymbols`)
- URL search params 状态(`useSearchParams` + `useRouter`)
- `KLineChart`(lightweight-charts:candlestick + MA overlay + volume histogram)
- `SymbolInfoCard` + `RecentBarsTable`
- 加载骨架 + 错误态 + 空缓存提示

### Milestone C — 报告列表 + Validate 详情(~1 天)

可见结果:报告列表 → 点详情 → 净值曲线 + 摘要 + 交易表。

- `/reports`:列表 + kind / since 过滤
- `/reports/[runId]`:`detail.kind` 分支
- `EquityChart`(line + drawdown area + 买卖 markers)
- `TradesTable`(sortable,paginate 20/页)
- `StatGrid`(4 stat 卡片)

### Milestone D — 选股(~1.5 天)

可见结果:配置因子 → 点开始 → 进度流式更新 → 候选股表展现。

- `FactorConfigPanel`(react-hook-form + zod,defaults 填初值)
- `useSelectionJobStream` + 单元测试(mock EventSource)
- `ProgressIndicator`(中文 stage label + 进度条)
- `SelectionResultsTable`(候选 + 因子分 + 命中 badges + 跳转看板)
- 配置面板可一键收起(320px ↔ 0px)
- `running > 15s` 显示"建议改用 CLI"提示
- CSV 导出

### Milestone E — Sweep 详情(~0.5 天)

可见结果:点 sweep 报告 → top combos 快报 + 全 sweep 表。

- `/reports/[runId]` 的 sweep 分支
- `SweepResultsTable`(按 `manifest.rank_by` 默认排序)
- `TopCombosCard`(从 `manifest.top_combos` 直读)

### Milestone F — 收尾(~0.5 天)

- `error.tsx` 每页一个
- 空状态文案 + Loading 骨架统一审查
- 中文文案审一遍(无英文残留)
- `web/README.md` + 主仓库 README / README-CN "前端开发"段落
- ADR-010 + devlog

**总工期**:~5 天(单人全职)。

---

## 9. 测试策略

| 层级 | 工具 | 测试对象 |
|---|---|---|
| 单元 | Vitest + React Testing Library | `lib/format.ts` / `lib/url-state.ts` / `lib/api.ts`(envelope + ApiError) |
| 单元 | Vitest + Mock EventSource | `useSelectionJobStream` 状态机(idle→running→done / failed / unmount cleanup) |
| 单元 | Vitest + MSW | TanStack Query 重试策略(5xx 第一次,200 第二次) |
| 类型 | TS strict + `pnpm gen:api` | 后端 schema 漂移即编译失败 |
| 集成 | 手动 | 真实后端 + 真实 reports/ + 真实缓存,手动过三页面 |

**必测**:`lib/sse.ts`、`lib/api.ts`、`lib/format.ts`、`lib/url-state.ts`。

**v1 不做**:Playwright E2E、Storybook、visual regression。

---

## 10. 已知风险

| 风险 | 应对 |
|---|---|
| `openapi-typescript` 对 FastAPI `Annotated[..., Query(...)]` 偶尔生成怪类型 | thin domain 层手动修正 |
| Next.js 15 客户端 `'use client'` 边界与 lightweight-charts hydration 冲突 | 所有 page 标 `'use client'`,确认无 hydration mismatch |
| lightweight-charts v5 在 React StrictMode 下重复初始化 | `useEffect` + ref + cleanup 严格管理实例生命周期 |
| 选股 job > 30s 用户以为卡死 | UI 在 `running > 15s` 显示提示 |
| SSE 在后端 reload 时断连 | EventSource 自带重连;v1 文档说明"刷新页面重连",不显式 polling fallback |

---

## 11. 决策记录

本 spec 的关键决策来自 brainstorming 对话:

- **Q1 框架 = Next.js (App Router)**:用户选择
- **Q2 位置 = `web/` 子目录**:同仓库 monorepo 子目录
- **Q3 视觉风格 = 借鉴 FinGOAT,Next.js 不变**:用户在看完 FinGOAT 是 Vite 后明确"风格学,框架不改"
- **Q4 图表 = `lightweight-charts` + ECharts(v2)**:K 线/净值用 LC,sweep 热图等延后
- **Q5 数据获取 = TanStack Query v5**:用户选择
- **视觉补充**:"主体要够大,圆角不要太抢戏,足够沉浸" → TopBar 收 44px、主图 0 圆角 full-bleed、单一 olive 强调色
- **SSE 仅用于选股**:其他全 TanStack Query 普通 GET
- **类型 = `openapi-typescript` 自动生成**:避免漂移
- **错误三档 + 4xx 不重试 + 5xx 重试 2 次**:用户认可
- **v1 不做 E2E / 热图 / 多窗口同步 / 移动端**:11 项非目标列表
