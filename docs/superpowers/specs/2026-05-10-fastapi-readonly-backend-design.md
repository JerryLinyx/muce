# FastAPI 只读后端设计

**日期**：2026-05-10
**状态**：设计已批准，待生成实施计划
**作者**：brainstorming session（Yuxuan + Claude）

---

## 1. 背景与目标

Muce 当前是一个 CLI-only 的 A 股研究/回测工具。下一步是给它加一个 Web 前端。本 spec 设计**第一阶段的 FastAPI 后端**，目标是支撑三个前端页面：

1. **标的看板**：浏览数据、查看 K 线和技术指标
2. **选股页**：选择因子、跑当日/某日选股、查看 Top-N 结果
3. **回测报告页**：浏览已有的 sweep / validate 回测结果

**范围（A+B 模式）**：
- 后端只读 + 同步触发短任务
- 长任务（全市场 sweep、backtrader validate）继续走 CLI 跑出报告，API 只展示
- 选股是 v1 唯一的"短任务触发"，需要进度推送（SSE）

**非目标（v1 明确不做）**：
- ❌ 用户 / 鉴权（默认放开本机源）
- ❌ 持久化 job state（重启丢任务，可接受）
- ❌ 多实例 / 横向扩展
- ❌ hit-rate / validation-gap 落盘成报告（v2）
- ❌ K 线 WebSocket / 实时推送
- ❌ 触发回测的 HTTP 接口
- ❌ 前端实现（本 spec 仅设计后端；UI 中文化是前端阶段的事，记录在此供后续阶段使用）

---

## 2. 整体架构

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│  FastAPI    │ ──▶ │ services/ 服务层 │ ──▶ │ 现有模块      │
│  (routes)   │     │ (新增,薄包装)     │     │ data/select/ │
└─────────────┘     └──────────────────┘     │  backtest/   │
                          ▲                  └──────────────┘
                          │                         │
                    CLI 也调用同一服务层              ▼
                                              Parquet 缓存
                                              reports/*.json
```

**核心约束**：

1. **业务逻辑只有一份**：`cli_*.py` 和 `api/routers/*.py` 都调用 `services/*_service.py` 里的同一个函数。
2. **services 层是同步纯函数**：返回 dataclass 或 DataFrame，不关心 HTTP / argparse。API 用 `asyncio.to_thread` 在线程池里跑。
3. **api 层不做业务**：路由函数只做 ① pydantic 入参校验 ② 调 service ③ 序列化 JSON。
4. **reports/ 模块独立**：CLI 写、API 读，两边都依赖它，独立于 services。

---

## 3. 模块布局

```
src/quant_backtest/
├── services/                  # 新增：业务逻辑层（CLI + API 共用）
│   ├── __init__.py
│   ├── data_service.py        # 标的查询、K线、缓存覆盖度
│   ├── selection_service.py   # 选股、因子描述、参数校验
│   └── reports_service.py     # 扫描 reports/ 目录、读 manifest
├── reports/                   # 新增：回测产物的 schema + 读写工具
│   ├── __init__.py
│   ├── schema.py              # ReportManifest / SweepManifest / ValidateManifest
│   └── store.py               # write_report / load_report / list_reports / load_artifact
├── api/                       # 新增：FastAPI 应用
│   ├── __init__.py
│   ├── app.py                 # FastAPI 实例 + 路由挂载 + run() 入口
│   ├── deps.py                # ParquetCache 依赖注入、配置读取
│   ├── errors.py              # 统一错误响应格式 (RFC 7807 风格)
│   ├── jobs.py                # 进程内 JobRegistry（选股进度用）
│   └── routers/
│       ├── __init__.py
│       ├── data.py            # /api/symbols, /api/bars/{symbol}, /api/cache/coverage
│       ├── selection.py       # /api/selection/*, jobs + SSE
│       └── reports.py         # /api/reports/*
└── cli_*.py                   # 现有 CLI：改为调用 services/，不再写业务
```

### 依赖

`pyproject.toml` 新增 optional extra：

```toml
[project.optional-dependencies]
api = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pydantic>=2.9",
  "sse-starlette>=2.1",
]
```

新增 console script：

```toml
[project.scripts]
quant-api = "quant_backtest.api.app:run"
```

启动命令：`uv sync --extra api && uv run quant-api`，等价于 `uvicorn quant_backtest.api.app:app --reload`。

---

## 4. API Endpoints

所有响应统一用 `{"data": ..., "meta": {...}}` 包裹；错误使用 RFC 7807 风格 `{"error": {"code", "message", "details"}}`。

### 4.1 数据路由（页面①）

| Method | Path | Service | 说明 |
|---|---|---|---|
| GET | `/api/symbols` | `data_service.list_symbols` | 搜索/列表，参数 `q=`（前缀/拼音匹配名称或代码）、`market=SH\|SZ`、`limit`、`offset` |
| GET | `/api/symbols/{symbol}` | `data_service.symbol_info` | 单标的基本信息（名称、市场、上市日、最新缓存日期） |
| GET | `/api/bars/{symbol}` | `data_service.load_bars_with_indicators` | K 线，参数 `start`、`end`、`adjust=qfq\|raw`、`indicators=ma_20,rsi_14,...` |
| GET | `/api/cache/coverage` | `data_service.cache_coverage` | 全市场缓存覆盖度（symbol → date range） |

**`GET /api/bars/{symbol}` 响应**：

```json
{
  "data": {
    "symbol": "000001.SZ",
    "adjust": "qfq",
    "indicators_requested": ["ma_20", "rsi_14"],
    "rows": [
      {"date": "2026-05-09", "open": 12.34, "high": 12.50, "low": 12.20,
       "close": 12.45, "volume": 1234567, "turnover": 15234567.89,
       "ma_20": 12.10, "rsi_14": 58.3}
    ]
  },
  "meta": {"rows": 612}
}
```

### 4.2 选股路由（页面②）

| Method | Path | Service | 说明 |
|---|---|---|---|
| GET | `/api/selection/factors` | 静态常量 | 6 个内置因子的元信息（key、中文名、描述、相关参数） |
| GET | `/api/selection/defaults` | 反射 dataclass | `FactorSelectorConfig` 默认值 + 字段说明 |
| POST | `/api/selection/jobs` | `JobRegistry.submit` | 启动一次选股任务，立即返回 `{job_id}`，后台线程开始跑 |
| GET | `/api/selection/jobs/{id}` | `JobRegistry.get` | 当前状态（pending / running / done / failed），done 时含 result |
| GET | `/api/selection/jobs/{id}/stream` | `JobRegistry.stream` | SSE 流，推阶段进度事件，done 时推 result |

**`POST /api/selection/jobs` 请求体**：

```json
{
  "as_of_date": "2026-05-09",
  "config": {
    "ma_short": 20, "ma_long": 60,
    "rsi_window": 14, "rsi_threshold": 55.0,
    "min_score": 2, "top_n": 20,
    "require_factors": ["ma_breakout"],
    "exclude_factors": [],
    "exclude_st": true, "exclude_suspended": true
  },
  "symbol_universe": null
}
```

`symbol_universe = null` 表示全市场；显式列表则只在该子集里筛。

**SSE 事件序列**（基于选股的天然阶段）：

```
event: progress
data: {"stage": "load_panel", "progress": 0.10, "message": "加载缓存面板..."}

event: progress
data: {"stage": "compute_indicators", "progress": 0.40, "message": "计算技术指标..."}

event: progress
data: {"stage": "score", "progress": 0.70, "message": "因子打分..."}

event: progress
data: {"stage": "filter_rank", "progress": 0.90, "message": "过滤 + Top-N 排序..."}

event: done
data: {"stage": "done", "progress": 1.00, "result": {...}}
```

**最终 `result` 结构**（与 `GET /jobs/{id}` 的 done 响应一致）：

```json
{
  "as_of_date": "2026-05-09",
  "config": { "...echo..." },
  "candidates": [
    {"symbol": "000001.SZ", "name": "平安银行", "score": 5,
     "factors_hit": ["ma_breakout", "rsi_momentum"],
     "reasons": "ma_breakout: close > ma_20; rsi_momentum: rsi=62.1>55"}
  ],
  "summary": {"total_universe": 5187, "passed_min_score": 312, "top_n_returned": 20}
}
```

**性能保护**：
- 结果缓存 key = hash(config + as_of_date + symbol_universe)；命中直接返回 done 状态，跳过任务
- 任务超时 30s（在 service 层 wall-clock 检查），超时把 job 标 failed + 提示"参数太重，建议改用 CLI"
- `JobRegistry` TTL 1 小时，单进程内存，重启丢失（可接受）

### 4.3 回测报告路由（页面③）

| Method | Path | Service | 说明 |
|---|---|---|---|
| GET | `/api/reports` | `reports_service.list_reports` | 列表，参数 `kind=sweep\|validate`、`since=YYYY-MM-DD`、`limit`，按 `created_at` 降序 |
| GET | `/api/reports/{id}` | `reports_service.load_report` | 单 report 的 manifest + 摘要指标 |
| GET | `/api/reports/{id}/equity` | `reports_service.load_equity` | 净值/回撤曲线（仅 validate 类型有） |
| GET | `/api/reports/{id}/trades` | `reports_service.load_trades` | 交易明细（仅 validate 类型有） |
| GET | `/api/reports/{id}/sweep` | `reports_service.load_sweep` | 参数 sweep 表（仅 sweep 类型有） |

`{id}` = report 目录名（`run_id`），见 §5。

### 4.4 系统路由

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查（含 Parquet 缓存目录是否可读、报告目录是否存在） |
| GET | `/api/version` | 项目版本 + 数据 provider 信息 |

---

## 5. 回测产物（reports/）schema

### 5.1 目录布局

```
reports/                              # 已在 .gitignore
├── sweeps/
│   └── {run_id}/
│       ├── manifest.json
│       ├── results.parquet
│       └── config.json
└── validations/
    └── {run_id}/
        ├── manifest.json
        ├── equity.parquet
        ├── trades.parquet
        ├── metrics.json
        └── config.json
```

**`run_id` 规则**：`{kind}-{yyyyMMdd-HHmmss}-{shortHash}`
- 例：`sweep-20260510-142233-a3f1c2`
- shortHash = config 内容哈希前 6 位
- **同 config 重跑产生不同 run_id**（时间不同），但能从 hash 后缀认出是同一组参数

### 5.2 Manifest schema

```python
# src/quant_backtest/reports/schema.py

@dataclass(frozen=True)
class DateRange:
    start: str  # ISO date
    end: str

@dataclass(frozen=True)
class ArtifactRef:
    name: str           # "equity" | "trades" | "results"
    path: str           # 相对 run_id 目录的相对路径
    rows: int

@dataclass(frozen=True)
class ReportManifest:
    run_id: str
    kind: Literal["sweep", "validate"]
    created_at: str           # ISO 8601 UTC, e.g. "2026-05-10T14:22:33Z"
    elapsed_seconds: float
    git_commit: str | None    # None if dirty/no-git
    git_dirty: bool
    data_range: DateRange
    symbols: list[str]
    config_hash: str          # 6-char hex, matches run_id suffix
    config_path: str          # "config.json"
    artifacts: list[ArtifactRef]

@dataclass(frozen=True)
class SweepManifest(ReportManifest):
    strategy: str             # "three-falling-buy-three-rising-sell" 等
    grid_size: int
    rank_by: str              # "total_return" / "sharpe" / ...
    top_combos: list[dict]    # top 5 组合的关键指标，方便列表页直接展示

@dataclass(frozen=True)
class ValidateManifest(ReportManifest):
    strategy: str
    signal_adjust: str        # "qfq"
    execution_adjust: str     # "raw"
    summary_metrics: dict     # {"total_return": 0.234, "sharpe": 1.12, "max_drawdown": -0.18, "trades": 47}
```

### 5.3 Parquet 列约定

**`equity.parquet`**：

```
date(date32) | cash(float64) | position_value(float64) | equity(float64)
            | drawdown(float64) | benchmark_equity(float64, nullable)
```

**`trades.parquet`**：

```
trade_id(int) | symbol(str) | direction(str: buy|sell) | open_date(date32)
| close_date(date32) | open_price(float64) | close_price(float64)
| size(int64) | pnl(float64) | pnl_pct(float64) | reason(str, nullable)
```

**`results.parquet`（sweep）**：

```
combo_id(int) | <参数列们>(根据 strategy 动态)
| total_return | sharpe | max_drawdown | win_rate | trades | ...
```

### 5.4 `reports/store.py` API

```python
def write_report(
    *,
    kind: str,                          # "sweep" | "validate"
    config: dict,
    manifest_extra: dict,               # 子类专属字段
    artifacts: dict[str, pd.DataFrame], # name -> df
    base_dir: Path = Path("reports"),
) -> str:                               # returns run_id
    ...

def list_reports(
    base_dir: Path,
    *,
    kind: str | None = None,
    since: date | None = None,
) -> list[ReportManifest]: ...

def load_report(base_dir: Path, run_id: str) -> ReportManifest: ...

def load_artifact(base_dir: Path, run_id: str, name: str) -> pd.DataFrame: ...
```

---

## 6. CLI 改造

| CLI 命令 | 现状 | 改造 |
|---|---|---|
| `quant-data download/update/inspect` | 直接调 cache 函数 | 改为调 `data_service`，行为不变 |
| `quant-backtest sweep` | 打印表格 | 仍然打印；**额外**调用 `write_report(kind="sweep", ...)`；新增可选 `--no-report` 关闭落盘 |
| `quant-backtest validate` | 打印指标 | 同上，落 `validations/{run_id}/` |
| `quant-select run` | 直接调 `factors.select_candidates` | 改为调 `selection_service.run_selection`，输出格式不变 |
| `quant-select hit-rate / validate-backtrader / diagnose-validation-gap` | 现有 v6/ artifacts | **v1 保持不变**，v2 再统一 |

**测试保护**：现有 [test_cli.py](tests/test_cli.py) 必须全过。

---

## 7. 测试策略

```
tests/
├── test_reports_store.py        # 新增：write→list→load round-trip + manifest schema
├── test_services_data.py        # 新增：list_symbols / load_bars / coverage 的 service 调用
├── test_services_selection.py   # 新增：service 层的 run_selection（含 on_progress 回调）
├── test_api_data.py             # 新增：FastAPI TestClient 打数据路由
├── test_api_selection.py        # 新增：job 启动 + SSE stream + 错误路径
├── test_api_reports.py          # 新增：list/详情/artifact 子资源
└── test_cli.py                  # 现有：扩展断言，确认 sweep/validate 落盘 + --no-report 行为
```

**关键测试用例**：

| 测试 | 验证什么 |
|---|---|
| CLI 重构无回归 | 现有 `test_cli.py` 全过，输出文本不变 |
| Reports round-trip | `write_report` → `list_reports` 能找到 → `load_report` 字段一致 → `load_artifact` 行数一致 |
| Service 选股进度回调 | 用 spy `on_progress`，断言收到 ≥4 个阶段事件 |
| SSE 流 | 用 `httpx.AsyncClient` 打 `/jobs/{id}/stream`，解析事件序列，确认末事件是 `done` + 含 `result` |
| Job 错误路径 | 故意传非法 config，断言 SSE 末事件是 `failed` + `error` 字段 |
| 选股结果缓存 | 同参数二次调用命中缓存（用 monkey-patch 计时器或缓存 spy） |
| API 错误格式 | 404/422 都返回 RFC 7807 风格 |

复用 `tests/conftest.py` 现有的 cache 构造 fixture，不重新造数据。

---

## 8. 实施顺序

每步都独立可提交、独立可验证。

### Step 1 — 抽 services 层（纯重构）

- 新增 `services/data_service.py` / `selection_service.py`
- 把 `cli_data.py` / `cli_selection.py` 的业务逻辑挪过去
- CLI 改为薄壳调用 service
- ✅ 验证：`pytest tests/test_cli.py` 全过

### Step 2 — reports 模块 + CLI 落盘

- 新增 `reports/schema.py` + `reports/store.py`
- `cli_backtest sweep/validate` 加上 `write_report` 调用 + `--no-report` 开关
- ✅ 验证：新增 `test_reports_store.py` + 跑一次真实 sweep 看 `reports/sweeps/...` 出现

### Step 3 — FastAPI 骨架 + 数据路由

- `pyproject.toml` 加 `api` extra + `quant-api` script
- `api/app.py` + `api/routers/data.py` + `api/errors.py`
- ✅ 验证：`uv run quant-api`，`curl /api/health` + `/api/symbols`

### Step 4 — 报告路由

- `api/routers/reports.py` + `services/reports_service.py`
- ✅ 验证：手动看 JSON，TestClient 测覆盖

### Step 5 — 选股路由 + Job 进度

- `api/jobs.py` 进程内 JobRegistry
- `selection_service.run_selection` 加 `on_progress` 参数
- `api/routers/selection.py` 三个端点 + SSE（`sse-starlette`）
- ✅ 验证：跑一次端到端，`curl -N` 模拟前端看流

### Step 6 — 收尾

- 错误中间件统一格式
- OpenAPI schema 自检（`/docs`）
- README 加"运行 API"段落
- 在 `docs/devlog/` 写一篇 `2026-05-10-fastapi-readonly-backend.md`
- 在 `docs/adr/` 加一篇 `0009-fastapi-readonly-backend.md`

---

## 9. 风险 & 开放问题

| 风险 | 影响 | 缓解 |
|---|---|---|
| 全市场选股同步执行可能 >30s | 用户看到超时 | 加结果缓存；超时给清晰提示让用户改用 CLI |
| services 抽取过程破坏 CLI 输出 | 测试失败 | 现有 `test_cli.py` 是回归保护；先跑测试再改 |
| SSE 在某些代理/浏览器下断流 | 进度推送不到前端 | 客户端断流后退回 polling `/jobs/{id}` |
| `reports/` 在多个 worktree 之间的可见性 | 同一份报告每个 worktree 都看到 | v1 接受；v2 可考虑用绝对路径 / 共享目录 |
| `git_commit` 在 dirty 仓库怎么记 | 重现性受损 | manifest 同时记 `git_dirty: true`，前端 UI 加警告 badge |

**v2 / 后续阶段**（不在本 spec 范围）：
- hit-rate / validation-gap 落盘统一
- 任务持久化（落 SQLite，重启不丢）
- 批量任务（一次跑多个选股配置对比）
- 前端实现（Next.js + ECharts/lightweight-charts，中文 UI）

---

## 10. 决策记录

本 spec 的关键决策来自 brainstorming 对话，简记如下：

- **范围 = A+B**（只读 + 同步触发短任务）：用户明确选择，避免引入 Redis/Celery
- **三个页面 = 看板/选股/回测报告**：用户明确指定
- **回测报告页只读**：用户选 A，CLI 跑、API 看
- **选股需要进度推送**：用户明确要求 → 引入 SSE + 进程内 JobRegistry
- **回测报告要带时间字段**：用户明确要求 → manifest 加 `created_at` / `elapsed_seconds` / `data_range` / `git_commit`
- **v1 报告类型 = sweep + validate**（推荐 B），hit-rate / gap 推迟到 v2
- **架构方案 = 1（薄壳 FastAPI）**：用户确认；不引入预跑层、不引入任务队列
