# Muce 牧策

> 多因子A股研究与回测工具箱，支持双引擎验证。
> *牧 — 牧养因子与信号；策 — 策略与决策。*

## 项目状态

**当前为研究 MVP**，尚非生产级实盘交易系统或组合管理平台。核心数据与回测基础设施已可运行，但工程层（统一模型、市场规则、风控）仍在建设中。

详细进度见 [docs/devlog/current/prd.md](docs/devlog/current/prd.md)（英文）。

## 当前进度

### 已完成 (P0-P3)

- ✅ **P0-1**：Simulator 与 Backtrader 差异诊断工具（迭代6次，差异从36%降至28%）
- ✅ **数据层**：Baostock 日线数据，支持 `qfq`（信号）与 `raw`（执行）复权模式
- ✅ **缓存**：Parquet 按数据源、复权模式、股票代码分区存储（约5200只股票，1年数据）
- ✅ **技术指标**：TA-Lib 集成，支持 RSI、Bollinger Bands、MACD、KDJ 等
- ✅ **全市场选股器**：多因子评分、硬过滤（require/exclude）、Top-N 排序
- ✅ **命中率验证**：因子归因与分层扫描命令
- ✅ **VectorBT 引擎**：基于缓存 A 股面板的快速参数扫描
- ✅ **Backtrader 引擎**：保守的事件驱动验证
- ✅ **只读 API**：FastAPI 服务，覆盖标的 / 选股（含 SSE 进度）/ 回测报告三组路由（详见 [ADR-009](docs/devlog/records/ADR-009_2026-05-10_fastapi-readonly-backend.md)）
- ✅ **回测产物落盘**：`reports/sweeps/{run_id}/` 与 `reports/validations/{run_id}/`，含 manifest + parquet + git 溯源
- ✅ **文档体系**：devlog、ADR、backlog、guides、brainstorm

### 进行中

- 🔄 **P0-4**：统一 Portfolio/Broker/Order/Fill 模型（P0-2/3/5 的基础设施）

### 计划中

- P0-2：Simulator 真实 Next-Open 仓位计算
- P0-3：策略级跳过候选股日志
- P0-5：A股市场规则引擎
- P0-6：特征与因子缓存
- P1-1：多年数据扩展（3-5年）
- P1-2：因子评估模块（IC、RankIC、分位数收益）
- P1-3：Walk-forward 与样本外验证
- P1-4：结果导出与研究产物管理
- P2-1：分钟数据与尾盘执行验证
- P2-2：模拟交易架构
- P2-3：风控层

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI 层                                   │
│  quant-data | quant-backtest | quant-select                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐
   │  数据   │   │  特征与   │   │  选股    │
   │ 提供商  │   │  技术指标  │   │  引擎    │
   └────┬────┘   └────┬─────┘   └────┬─────┘
        │             │              │
        ▼             ▼              ▼
   ┌─────────────────────────────────────────┐
   │           双回测引擎                      │
   │  VectorBT (快速扫描) │ Backtrader (验证) │
   └─────────────────────────────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   诊断工具            │
            │ diagnose-validation-gap │
            └─────────────────────┘
```

## 安装

```bash
uv sync --extra test
```

可选依赖：

```bash
uv sync --extra data      # 数据下载依赖
uv sync --extra research  # VectorBT 研究依赖
uv sync --extra validation # Backtrader 验证依赖
uv sync --extra all       # 全部依赖
```

## 快速开始

### 数据命令

```bash
# 下载日线数据（前复权，用于信号）
uv run quant-data download --symbols 000001.SZ,600000.SH --start 20200101 --end 20251231 --adjust qfq

# 下载日线数据（未复权，用于执行价）
uv run quant-data download --symbols 000001.SZ,600000.SH --start 20200101 --end 20251231 --adjust raw

# 查看数据
uv run quant-data inspect --symbols 000001.SZ,600000.SH --adjust qfq
```

### 回测命令

```bash
# Backtrader 验证（SMA 交叉策略）
uv run quant-backtest validate \
  --symbols 000001.SZ \
  --signal-adjust qfq \
  --execution-adjust raw \
  --fast-period 5 \
  --slow-period 20

# VectorBT 参数扫描
uv run quant-backtest sweep \
  --symbols 603986.SH \
  --strategy three-falling-buy-three-rising-sell \
  --signal-counts 2,3,4 \
  --rank-by total_return
```

回测命令默认会把 manifest + parquet 落到 `reports/`。加 `--no-report` 跳过，或 `--reports-dir <path>` 改写位置。

### 启动只读 API

```bash
uv sync --extra api
uv run quant-api          # 默认监听 127.0.0.1:8000
```

浏览器打开 `http://127.0.0.1:8000/docs` 即可看到 OpenAPI 文档。三组核心路由：

- `/api/symbols`、`/api/bars/{symbol}`、`/api/cache/coverage`：标的看板
- `/api/selection/{factors,defaults,jobs,jobs/{id},jobs/{id}/stream}`：选股（异步任务 + SSE 进度）
- `/api/reports`、`/api/reports/{id}/{equity,trades,sweep}`：回测报告

环境变量：`MUCE_API_HOST`、`MUCE_API_PORT`、`MUCE_API_RELOAD`、`MUCE_CACHE_ROOT`、`MUCE_REPORTS_DIR`、`MUCE_API_CORS_ORIGINS`（前端 CORS 白名单，默认放行 `localhost:3000` 与 `localhost:5173`）。

### 选股命令

```bash
# 全市场日线选股（RSI + Bollinger）
uv run quant-select daily \
  --start 20240101 \
  --end 20241231 \
  --rsi-threshold 70 \
  --bollinger-period 15 \
  --top-n 10

# 命中率分析
uv run quant-select hit-rate \
  --start 20240101 \
  --end 20241231 \
  --rsi-threshold 70

# 诊断 Simulator 与 Backtrader 差异
uv run quant-select diagnose-validation-gap \
  --selector-config rsi70-boll15
```

VectorBT 使用整数股数粒度（`--size-granularity 1`）以保持与 Backtrader 语义一致。

## 项目结构

```
muce/
├── src/quant_backtest/
│   ├── data/           # 数据提供商、缓存、DuckDB 查询
│   ├── features/       # 技术指标（TA-Lib）
│   ├── backtest/       # VectorBT 与 Backtrader 引擎
│   ├── selection/      # 选股器、命中率、诊断
│   └── cli_*.py        # CLI 入口
├── tests/              # 单元与集成测试
├── docs/               # 文档（devlog、ADR、guides）
│   ├── devlog/         # 开发日志
│   ├── adr/            # 架构决策记录
│   ├── requirements/   # 优先级路线图
│   └── guides/         # 操作指南
├── reports/            # 回测与验证产物
└── data/               # 本地缓存（Parquet）
```

### 启动 Web 前端

前端位于 `web/`，Next.js 16 App Router 单页应用。

首次安装：

```bash
cd web
npm install
```

同时启动后端和前端（两个终端）：

```bash
# 终端 1（仓库根）
uv run quant-api

# 终端 2（仓库根）
cd web && npm run dev
```

浏览器打开 <http://localhost:3000>。前端通过 Next.js rewrites 把 `/api/*`
反代到 `http://127.0.0.1:8000`。三个页面分别是看板、选股、报告。

后端 schema 变更后重新生成前端类型：

```bash
cd web && npm run gen:api
```

## 文档

- [docs/README.md](docs/README.md) - 文档索引
- [docs/devlog/current/prd.md](docs/devlog/current/prd.md) - 详细进度跟踪（英文）
- [docs/devlog/appendix/backtrader-validation.md](docs/devlog/appendix/backtrader-validation.md) - Backtrader 验证指南

## 许可证

本项目采用 **GNU 通用公共许可证 v3.0 或更高版本**（GPL-3.0-or-later）。详见 [LICENSE](LICENSE)。

选择 GPL-3.0 是因为项目依赖 `backtrader`（GPL-3.0）。任何再分发（GitHub 分叉、源码发布、二进制分发）必须保持 GPL-3.0 兼容。

### 第三方许可证

| 包 | 许可证 | 说明 |
|---------|---------|-------|
| `backtrader` | GPL-3.0 | 传染性开源。强制本项目 GPL-3.0。 |
| `vectorbt`（免费版） | Apache-2.0 + **Commons Clause** | **仅限个人/非商业使用**。 |
| `baostock` | BSD-3-Clause | 宽松。 |
| `pandas`, `pyarrow`, `duckdb` | Apache-2.0 / BSD-style | 宽松。 |
| `ta-lib`（可选） | BSD | 宽松。 |

### 允许使用

- ✅ 个人研究、自用实盘、学术工作
- ✅ GPL-3.0 下的开源分发（免费 GitHub 分叉）
- ✅ 内部使用（不对外分发或销售）

### 替换依赖后方可使用

- ❌ 在依赖 `vectorbt`（免费版）的情况下销售项目 — Commons Clause 禁止
- ❌ 在依赖 `backtrader` 的情况下发布闭源二进制 — GPL-3.0 禁止