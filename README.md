# Muce 牧策

> Multi-factor A-share research and backtesting toolkit with dual-engine validation.
> *牧 — shepherding factors and signals; 策 — strategy and decisions.*

A-share data layer for research backtesting:

- `baostock` provider as the implemented source.
- `qfq` data for signals and sweeps, `raw` data for execution-price validation.
- Parquet cache partitioned by source, adjust mode, and symbol.
- Separate adapters for vectorbt-style wide panels and backtrader-style single-symbol feeds.
- Backtrader validation engine with raw execution prices and qfq signal lines.
- VectorBT research engine for fast parameter sweeps over cached A-share panels.

Detailed design and development notes live in [docs/README.md](docs/README.md).
中文 README：[README-CN.md](README-CN.md)。进度跟踪：[docs/devlog/current/prd.md](docs/devlog/current/prd.md)。

Install with uv:

```bash
uv sync --extra test
```

Optional runtime extras:

```bash
uv sync --extra data
uv sync --extra research
uv sync --extra validation
uv sync --extra all
```

Example data commands:

```bash
uv run quant-data download --symbols 000001.SZ,600000.SH --start 20200101 --end 20251231 --adjust qfq
uv run quant-data download --symbols 000001.SZ,600000.SH --start 20200101 --end 20251231 --adjust raw
uv run quant-data inspect --symbols 000001.SZ,600000.SH --adjust qfq
```

Run a backtrader validation with the built-in signal SMA cross strategy:

```bash
uv run quant-backtest validate \
  --symbols 000001.SZ \
  --signal-adjust qfq \
  --execution-adjust raw \
  --fast-period 5 \
  --slow-period 20
```

Run a vectorbt sweep:

```bash
uv run quant-backtest sweep \
  --symbols 603986.SH \
  --strategy three-falling-buy-three-rising-sell \
  --signal-counts 2,3,4 \
  --rank-by total_return
```

VectorBT defaults to integer share granularity (`--size-granularity 1`) so research sweeps stay close to Backtrader validation semantics.

## Run the read-only API

Install the API extra:

```bash
uv sync --extra api
```

Start the server:

```bash
uv run quant-api
# or, with auto-reload:
MUCE_API_RELOAD=1 uv run quant-api
```

Browse interactive docs at http://127.0.0.1:8000/docs. The API is read-only;
backtest sweeps and validations stay in the CLI and produce report artifacts
the API serves back.

Endpoints:

- `GET  /api/health`, `/api/version`
- `GET  /api/symbols`, `/api/symbols/{symbol}` — symbol search and basic info
- `GET  /api/bars/{symbol}` — K-line + optional indicators (`?indicators=ma_20,rsi_14`)
- `GET  /api/cache/coverage` — full-market cache coverage
- `GET  /api/selection/factors`, `/api/selection/defaults` — factor metadata
- `POST /api/selection/jobs` — start a selection (returns `{job_id}`)
- `GET  /api/selection/jobs/{id}` — poll status (`pending` / `running` / `done` / `failed`)
- `GET  /api/selection/jobs/{id}/stream` — Server-Sent Events progress + result
- `GET  /api/reports`, `/api/reports/{id}` — list / detail of CLI-produced reports
- `GET  /api/reports/{id}/equity|trades|sweep` — per-artifact JSON

`quant-backtest sweep` and `quant-backtest validate` write reports to
`reports/sweeps/{run_id}/` and `reports/validations/{run_id}/` by default.
Pass `--no-report` to skip on-disk output, or `--reports-dir <path>` to
redirect.

## License

This project is released under the **GNU General Public License v3.0 or later** (GPL-3.0-or-later). See [LICENSE](LICENSE) for the full text.

GPL-3.0 was selected because the project depends on `backtrader` (GPL-3.0). Any redistribution of this codebase — public GitHub fork, source release, or binary distribution — must remain GPL-3.0-compatible.

### Third-Party Licenses

Runtime and optional dependencies retain their own licenses. Notable terms that affect how this project may be used:

| Package | License | Notes |
|---------|---------|-------|
| `backtrader` | GPL-3.0 | Copyleft. Forces this project to be GPL-3.0. |
| `vectorbt` (free tier) | Apache-2.0 + **Commons Clause** | **Personal / non-commercial use only.** The Commons Clause prohibits selling any product or service whose value derives substantially from `vectorbt`. |
| `baostock` | BSD-3-Clause | Permissive. |
| `pandas`, `pyarrow`, `duckdb` | Apache-2.0 / BSD-style | Permissive. |
| `ta-lib` (optional) | BSD | Permissive. |

### Permitted Use

- ✅ Personal research, self-directed live trading, academic work.
- ✅ Free open-source distribution under GPL-3.0 (e.g. public GitHub fork that does not charge fees).
- ✅ Internal use within an organization that does not redistribute or sell access.

### Not Permitted Without Replacing Dependencies

- ❌ Selling the project (or a derivative) as a paid product, hosted SaaS, or fee-based consulting offering, while it depends on `vectorbt` (free tier). The Commons Clause forbids this.
- ❌ Releasing a closed-source binary or commercial fork while it depends on `backtrader`. GPL-3.0 forbids this.

If commercial use becomes a goal, `vectorbt` (free tier) must be removed or replaced (e.g. by `vectorbt PRO` under a commercial license, or by an alternative engine such as `bt` / `zipline-reloaded` / a custom vectorized engine), and the `backtrader` dependency must either remain GPL-compatible or be replaced.
