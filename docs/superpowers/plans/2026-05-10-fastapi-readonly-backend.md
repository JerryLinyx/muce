# FastAPI Read-Only Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a thin FastAPI backend that exposes Muce's existing `quant_backtest` modules to a future web UI through three resource groups — symbol data, daily selection (with SSE progress), and read-only backtest reports.

**Architecture:** A three-layer split — `services/` (shared business logic, sync, pure functions) ← called by both `cli_*.py` and `api/routers/*.py` (HTTP-only concerns). A new `reports/` module defines a stable on-disk artifact format that CLI writes and API reads. An in-process `JobRegistry` + `sse-starlette` powers selection progress. No queue, no DB, no auth.

**Tech Stack:** Python 3.11+, FastAPI ≥0.115, Uvicorn, Pydantic v2, sse-starlette ≥2.1, pandas, pyarrow. Package managed by `uv`. Tests via pytest with `httpx.AsyncClient` for SSE.

**Spec:** [docs/superpowers/specs/2026-05-10-fastapi-readonly-backend-design.md](../specs/2026-05-10-fastapi-readonly-backend-design.md)

---

## File Structure

### Created

| Path | Responsibility |
|---|---|
| `src/quant_backtest/services/__init__.py` | Service layer exports |
| `src/quant_backtest/services/data_service.py` | Symbol search, K-line+indicators, cache coverage |
| `src/quant_backtest/services/selection_service.py` | `run_selection(...)` with `on_progress` callback |
| `src/quant_backtest/services/reports_service.py` | List/load reports from `reports/` |
| `src/quant_backtest/reports/__init__.py` | Re-export `schema` and `store` |
| `src/quant_backtest/reports/schema.py` | `ReportManifest` / `SweepManifest` / `ValidateManifest` dataclasses |
| `src/quant_backtest/reports/store.py` | `write_report` / `list_reports` / `load_report` / `load_artifact` |
| `src/quant_backtest/api/__init__.py` | API package marker |
| `src/quant_backtest/api/app.py` | FastAPI() instance + `run()` entrypoint + router mounting |
| `src/quant_backtest/api/deps.py` | `get_cache()` / `get_reports_dir()` dependency injection |
| `src/quant_backtest/api/errors.py` | Unified RFC 7807 error envelope |
| `src/quant_backtest/api/jobs.py` | In-process `JobRegistry` (TTL 1h) |
| `src/quant_backtest/api/schemas.py` | Pydantic request/response models |
| `src/quant_backtest/api/routers/__init__.py` | Router package marker |
| `src/quant_backtest/api/routers/data.py` | `/api/symbols`, `/api/bars/...`, `/api/cache/coverage` |
| `src/quant_backtest/api/routers/selection.py` | `/api/selection/*` including jobs + SSE |
| `src/quant_backtest/api/routers/reports.py` | `/api/reports/*` |
| `src/quant_backtest/api/routers/system.py` | `/api/health`, `/api/version` |
| `tests/test_reports_store.py` | Round-trip write→list→load |
| `tests/test_services_data.py` | Service layer for data |
| `tests/test_services_selection.py` | Service layer + `on_progress` callback |
| `tests/test_api_health.py` | API skeleton smoke tests |
| `tests/test_api_data.py` | TestClient against data router |
| `tests/test_api_reports.py` | TestClient against reports router |
| `tests/test_api_selection.py` | Job lifecycle + SSE stream |
| `docs/devlog/2026-05-10-fastapi-readonly-backend.md` | Devlog |
| `docs/adr/0009-fastapi-readonly-backend.md` | ADR |

### Modified

| Path | What changes |
|---|---|
| `pyproject.toml` | Add `api` extra; add `quant-api` script entry |
| `src/quant_backtest/cli_data.py` | Refactor to call `data_service` |
| `src/quant_backtest/cli_selection.py` | Refactor `candidates` subcommand to call `selection_service.run_selection` |
| `src/quant_backtest/cli_backtest.py` | `sweep`/`validate` subcommands call `write_report` (default on); add `--no-report` flag |
| `tests/test_cli.py` | Add assertions for report-on-disk side effects + `--no-report` |
| `README.md` | Add "Run the API" section |

---

## Phase 1 — Services Layer (Pure Refactor)

Goal: extract business logic from CLI into `services/` so both CLI and API can call it. **Behavior must not change** — `tests/test_cli.py` is the regression net.

### Task 1.1: Establish services package

**Files:**
- Create: `src/quant_backtest/services/__init__.py`

- [ ] **Step 1: Create empty package**

```python
"""Service layer shared by CLI and API entry points."""

from __future__ import annotations
```

- [ ] **Step 2: Confirm package importable**

Run: `uv run python -c "import quant_backtest.services"`
Expected: no output, exit 0

- [ ] **Step 3: Commit**

```bash
git add src/quant_backtest/services/__init__.py
git commit -m "feat(services): establish empty service layer package"
```

### Task 1.2: Data service — list_symbols & symbol_info

**Files:**
- Create: `src/quant_backtest/services/data_service.py`
- Create: `tests/test_services_data.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_services_data.py
from __future__ import annotations

import pandas as pd
import pytest

from quant_backtest.data.cache import ParquetCache
from quant_backtest.services import data_service


@pytest.fixture()
def cache_with_symbols(tmp_path) -> ParquetCache:
    cache = ParquetCache(tmp_path)
    frame = pd.DataFrame({
        "symbol": ["000001.SZ", "000001.SZ", "600000.SH"],
        "date": pd.to_datetime(["2026-05-08", "2026-05-09", "2026-05-09"]),
        "open": [10.0, 10.5, 8.0],
        "high": [10.6, 11.0, 8.4],
        "low": [9.9, 10.3, 7.9],
        "close": [10.5, 10.8, 8.2],
        "volume": [1_000_000, 1_100_000, 800_000],
        "turnover": [1.0e7, 1.1e7, 6.5e6],
        "source": ["baostock"] * 3,
        "adjust": ["qfq"] * 3,
    })
    cache.write(frame)
    return cache


def test_list_symbols_returns_all(cache_with_symbols):
    rows = data_service.list_symbols(cache_with_symbols, adjust="qfq")
    assert {row.symbol for row in rows} == {"000001.SZ", "600000.SH"}


def test_list_symbols_filters_by_market(cache_with_symbols):
    rows = data_service.list_symbols(cache_with_symbols, adjust="qfq", market="SZ")
    assert [row.symbol for row in rows] == ["000001.SZ"]


def test_list_symbols_query_prefix(cache_with_symbols):
    rows = data_service.list_symbols(cache_with_symbols, adjust="qfq", query="000")
    assert [row.symbol for row in rows] == ["000001.SZ"]


def test_symbol_info_returns_latest_date(cache_with_symbols):
    info = data_service.symbol_info(cache_with_symbols, "000001.SZ", adjust="qfq")
    assert info.symbol == "000001.SZ"
    assert info.market == "SZ"
    assert str(info.last_cached_date) == "2026-05-09"
```

- [ ] **Step 2: Run test, confirm failure**

Run: `uv run pytest tests/test_services_data.py -v`
Expected: FAIL with `ModuleNotFoundError: ... data_service`

- [ ] **Step 3: Implement data_service skeleton**

```python
# src/quant_backtest/services/data_service.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import SOURCE_BAOSTOCK


@dataclass(frozen=True)
class SymbolRow:
    symbol: str
    market: str  # "SZ" | "SH" | "BJ"
    last_cached_date: date | None


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str
    market: str
    last_cached_date: date | None


def list_symbols(
    cache: ParquetCache,
    *,
    adjust: str = "qfq",
    source: str = SOURCE_BAOSTOCK,
    query: str | None = None,
    market: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[SymbolRow]:
    symbols = cache.available_symbols(source=source, adjust=adjust)
    rows: list[SymbolRow] = []
    for symbol in sorted(symbols):
        market_code = symbol.split(".")[-1]
        if market and market_code != market:
            continue
        if query and not symbol.startswith(query):
            continue
        last_date = cache.last_date(symbol, source=source, adjust=adjust)
        rows.append(SymbolRow(symbol=symbol, market=market_code, last_cached_date=last_date))
    if offset:
        rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]
    return rows


def symbol_info(
    cache: ParquetCache,
    symbol: str,
    *,
    adjust: str = "qfq",
    source: str = SOURCE_BAOSTOCK,
) -> SymbolInfo:
    market = symbol.split(".")[-1]
    last_date = cache.last_date(symbol, source=source, adjust=adjust)
    return SymbolInfo(symbol=symbol, market=market, last_cached_date=last_date)
```

- [ ] **Step 4: Verify ParquetCache surface matches**

Run: `uv run python -c "from quant_backtest.data.cache import ParquetCache; print([m for m in dir(ParquetCache) if not m.startswith('_')])"`
Expected output contains `available_symbols` and `last_date`. If `last_date` requires extra args, adapt the implementation accordingly using `inspect()` results.

- [ ] **Step 5: Run tests, confirm pass**

Run: `uv run pytest tests/test_services_data.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/quant_backtest/services/data_service.py tests/test_services_data.py
git commit -m "feat(services): add data_service.list_symbols and symbol_info"
```

### Task 1.3: Data service — load_bars_with_indicators

**Files:**
- Modify: `src/quant_backtest/services/data_service.py`
- Modify: `tests/test_services_data.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_services_data.py`:

```python
def test_load_bars_returns_rows(cache_with_symbols):
    result = data_service.load_bars_with_indicators(
        cache_with_symbols, "000001.SZ", adjust="qfq", indicators=()
    )
    assert result.symbol == "000001.SZ"
    assert result.adjust == "qfq"
    assert len(result.rows) == 2
    first = result.rows[0]
    assert first["date"] == "2026-05-08"
    assert first["close"] == pytest.approx(10.5)


def test_load_bars_with_indicators(cache_with_symbols):
    result = data_service.load_bars_with_indicators(
        cache_with_symbols, "000001.SZ", adjust="qfq", indicators=("ma_2",)
    )
    assert "ma_2" in result.rows[-1]
    assert result.rows[-1]["ma_2"] == pytest.approx(10.65)
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_services_data.py::test_load_bars_returns_rows -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'load_bars_with_indicators'`

- [ ] **Step 3: Implement**

Append to `src/quant_backtest/services/data_service.py`:

```python
from quant_backtest.features.indicators import (
    TechnicalIndicatorConfig,
    add_technical_indicators,
)


@dataclass(frozen=True)
class BarsResult:
    symbol: str
    adjust: str
    indicators_requested: tuple[str, ...]
    rows: list[dict]


def load_bars_with_indicators(
    cache: ParquetCache,
    symbol: str,
    *,
    adjust: str = "qfq",
    source: str = SOURCE_BAOSTOCK,
    start: date | None = None,
    end: date | None = None,
    indicators: tuple[str, ...] = (),
) -> BarsResult:
    df = cache.read_symbol(symbol, source=source, adjust=adjust)
    if start is not None:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df["date"] <= pd.Timestamp(end)]
    if indicators:
        ma_windows = tuple(
            sorted({int(name.split("_")[1]) for name in indicators if name.startswith("ma_")})
        )
        rsi_windows = [int(name.split("_")[1]) for name in indicators if name.startswith("rsi_")]
        config = TechnicalIndicatorConfig(
            ma_windows=ma_windows or (20,),
            rsi_window=rsi_windows[0] if rsi_windows else 14,
        )
        df = add_technical_indicators(df, config=config)
    rows = []
    for record in df.to_dict(orient="records"):
        record["date"] = pd.Timestamp(record["date"]).strftime("%Y-%m-%d")
        rows.append({k: v for k, v in record.items() if k in {"date","open","high","low","close","volume","turnover", *indicators}})
    return BarsResult(symbol=symbol, adjust=adjust, indicators_requested=tuple(indicators), rows=rows)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_services_data.py -v`
Expected: 6 passed

If `TechnicalIndicatorConfig` has a different signature in this repo, adjust the kwargs to match `src/quant_backtest/features/indicators.py`. The test only requires `ma_2` to compute as the 2-period mean.

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/services/data_service.py tests/test_services_data.py
git commit -m "feat(services): add load_bars_with_indicators"
```

### Task 1.4: Data service — cache coverage

**Files:**
- Modify: `src/quant_backtest/services/data_service.py`
- Modify: `tests/test_services_data.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_services_data.py`:

```python
def test_cache_coverage(cache_with_symbols):
    coverage = data_service.cache_coverage(cache_with_symbols, adjust="qfq")
    by_symbol = {entry.symbol: entry for entry in coverage}
    assert by_symbol["000001.SZ"].rows == 2
    assert str(by_symbol["000001.SZ"].first_date) == "2026-05-08"
    assert str(by_symbol["000001.SZ"].last_date) == "2026-05-09"
    assert by_symbol["600000.SH"].rows == 1
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_services_data.py::test_cache_coverage -v`
Expected: FAIL — attribute error

- [ ] **Step 3: Implement**

Append to `src/quant_backtest/services/data_service.py`:

```python
@dataclass(frozen=True)
class CoverageEntry:
    symbol: str
    rows: int
    first_date: date | None
    last_date: date | None


def cache_coverage(
    cache: ParquetCache,
    *,
    adjust: str = "qfq",
    source: str = SOURCE_BAOSTOCK,
) -> list[CoverageEntry]:
    inspections = cache.inspect(source=source, adjust=adjust)
    entries: list[CoverageEntry] = []
    for ins in inspections:
        entries.append(
            CoverageEntry(
                symbol=ins.symbol,
                rows=ins.rows,
                first_date=ins.first_date,
                last_date=ins.last_date,
            )
        )
    return entries
```

If `cache.inspect` returns a different shape, run `uv run python -c "from quant_backtest.data.cache import ParquetCache; help(ParquetCache.inspect)"` and adapt — the goal is to surface (symbol, rows, first_date, last_date) per cached symbol.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_services_data.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/services/data_service.py tests/test_services_data.py
git commit -m "feat(services): add cache_coverage"
```

### Task 1.5: Selection service — run_selection (no progress yet)

**Files:**
- Create: `src/quant_backtest/services/selection_service.py`
- Create: `tests/test_services_selection.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_services_selection.py
from __future__ import annotations

import pandas as pd
import pytest

from quant_backtest.data.cache import ParquetCache
from quant_backtest.selection import FactorSelectorConfig
from quant_backtest.services import selection_service


@pytest.fixture()
def populated_cache(tmp_path) -> ParquetCache:
    """Build a tiny cache with a symbol that satisfies ma_breakout."""
    dates = pd.bdate_range("2026-01-01", periods=80)
    closes = [10.0 + i * 0.1 for i in range(80)]
    frame = pd.DataFrame({
        "symbol": ["000001.SZ"] * 80,
        "date": dates,
        "open": closes,
        "high": [c + 0.2 for c in closes],
        "low":  [c - 0.2 for c in closes],
        "close": closes,
        "volume": [1_000_000] * 80,
        "turnover": [c * 1_000_000 for c in closes],
        "source": ["baostock"] * 80,
        "adjust": ["qfq"] * 80,
    })
    cache = ParquetCache(tmp_path)
    cache.write(frame)
    return cache


def test_run_selection_returns_candidates(populated_cache):
    config = FactorSelectorConfig(min_score=1, top_n=5)
    result = selection_service.run_selection(
        cache=populated_cache,
        config=config,
        as_of_date=None,  # latest
        symbols=None,
    )
    assert result.as_of_date is not None
    assert isinstance(result.candidates, list)
    assert result.summary["total_universe"] == 1


def test_run_selection_respects_symbols(populated_cache):
    config = FactorSelectorConfig(min_score=0, top_n=5)
    result = selection_service.run_selection(
        cache=populated_cache,
        config=config,
        as_of_date=None,
        symbols=["000001.SZ"],
    )
    assert result.summary["total_universe"] == 1
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_services_selection.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement**

```python
# src/quant_backtest/services/selection_service.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable

import pandas as pd

from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import SOURCE_BAOSTOCK
from quant_backtest.selection import (
    FactorSelectorConfig,
    build_factor_table,
    select_candidates,
)


ProgressCallback = Callable[[str, float, str], None]


@dataclass(frozen=True)
class SelectionResult:
    as_of_date: str
    config: dict
    candidates: list[dict]
    summary: dict


def _noop(stage: str, progress: float, message: str) -> None:
    return None


def run_selection(
    *,
    cache: ParquetCache,
    config: FactorSelectorConfig,
    as_of_date: date | str | None = None,
    symbols: list[str] | None = None,
    source: str = SOURCE_BAOSTOCK,
    adjust: str = "qfq",
    on_progress: ProgressCallback | None = None,
) -> SelectionResult:
    progress = on_progress or _noop

    progress("load_panel", 0.10, "加载缓存面板...")
    universe = symbols or cache.available_symbols(source=source, adjust=adjust)
    panel = cache.read_many(symbols=universe, source=source, adjust=adjust)

    progress("compute_indicators", 0.40, "计算技术指标...")
    factor_table = build_factor_table(panel, config=config)

    progress("score", 0.70, "因子打分...")
    if as_of_date is None:
        as_of = factor_table["date"].max()
    else:
        as_of = pd.Timestamp(as_of_date)
    snapshot = factor_table[factor_table["date"] == as_of].copy()

    progress("filter_rank", 0.90, "过滤 + Top-N 排序...")
    candidates_frame = select_candidates(snapshot, config=config)

    candidates = []
    for record in candidates_frame.to_dict(orient="records"):
        candidates.append({
            "symbol": record.get("symbol"),
            "score": int(record.get("score", 0)),
            "factors_hit": [
                col for col in record
                if col.startswith(("ma_breakout","kdj_golden","macd_golden","rsi_momentum","volume_breakout","boll_breakout"))
                and record[col]
            ],
            "reasons": record.get("reasons", ""),
        })

    summary = {
        "total_universe": len(universe),
        "passed_min_score": int(len(candidates_frame)),
        "top_n_returned": int(min(len(candidates_frame), config.top_n)),
    }
    progress("done", 1.0, "完成")
    return SelectionResult(
        as_of_date=str(pd.Timestamp(as_of).date()),
        config=_config_to_dict(config),
        candidates=candidates,
        summary=summary,
    )


def _config_to_dict(config: FactorSelectorConfig) -> dict:
    from dataclasses import asdict
    payload = asdict(config)
    payload["require_factors"] = list(config.require_factors)
    payload["exclude_factors"] = list(config.exclude_factors)
    return payload
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_services_selection.py -v`
Expected: 2 passed

If `select_candidates` returns a DataFrame whose factor-hit columns differ, list them by inspecting the columns programmatically. The point of the test is structural: a `candidates` list and a `summary` dict.

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/services/selection_service.py tests/test_services_selection.py
git commit -m "feat(services): add selection_service.run_selection"
```

### Task 1.6: Selection service — on_progress callback test

**Files:**
- Modify: `tests/test_services_selection.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_selection_emits_progress(populated_cache):
    events: list[tuple[str, float, str]] = []
    config = FactorSelectorConfig(min_score=0, top_n=5)
    selection_service.run_selection(
        cache=populated_cache,
        config=config,
        as_of_date=None,
        symbols=["000001.SZ"],
        on_progress=lambda stage, progress, msg: events.append((stage, progress, msg)),
    )
    stages = [stage for stage, _, _ in events]
    assert stages == ["load_panel", "compute_indicators", "score", "filter_rank", "done"]
    assert events[-1][1] == 1.0
```

- [ ] **Step 2: Run, confirm pass**

Run: `uv run pytest tests/test_services_selection.py::test_run_selection_emits_progress -v`
Expected: PASS (callback already wired in Task 1.5)

- [ ] **Step 3: Commit**

```bash
git add tests/test_services_selection.py
git commit -m "test(services): assert on_progress emits the five expected stages"
```

### Task 1.7: Wire CLI to services (no behavior change)

**Files:**
- Modify: `src/quant_backtest/cli_data.py`
- Modify: `src/quant_backtest/cli_selection.py` (only the `candidates` subcommand)

- [ ] **Step 1: Run baseline CLI tests, capture green state**

Run: `uv run pytest tests/test_cli.py -v`
Expected: ALL passing. Record count for diff.

- [ ] **Step 2: Refactor `cli_data.py` `inspect` and `download` paths**

Replace direct `cache.inspect(...)` / `cache.available_symbols(...)` calls in the inspect/list paths with `data_service.list_symbols` / `data_service.cache_coverage`. Other operations (download/update) keep talking to `cache` directly — they are write-side and out of scope for the read-only API.

- [ ] **Step 3: Refactor `cli_selection.py` `candidates` subcommand**

Locate the `candidates` subcommand handler. Build a `FactorSelectorConfig` from args (existing logic — keep it), call `selection_service.run_selection(cache=..., config=..., as_of_date=args.date, symbols=resolved_symbols)`, then format the result back into the CLI's existing print layout. Do not change stdout formatting.

- [ ] **Step 4: Run CLI tests**

Run: `uv run pytest tests/test_cli.py -v`
Expected: same count of tests still pass. If any fail, the refactor changed observable behavior — diff and fix until green.

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: ALL pass (services tests + CLI tests + everything else)

- [ ] **Step 6: Commit**

```bash
git add src/quant_backtest/cli_data.py src/quant_backtest/cli_selection.py
git commit -m "refactor(cli): route data and candidates through service layer"
```

---

## Phase 2 — Reports Module + CLI Write-Through

### Task 2.1: Reports schema dataclasses

**Files:**
- Create: `src/quant_backtest/reports/__init__.py`
- Create: `src/quant_backtest/reports/schema.py`
- Create: `tests/test_reports_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reports_store.py
from __future__ import annotations

from quant_backtest.reports.schema import (
    DateRange,
    ArtifactRef,
    ReportManifest,
    SweepManifest,
    ValidateManifest,
)


def test_report_manifest_to_dict_round_trip():
    manifest = ReportManifest(
        run_id="sweep-20260510-142233-a3f1c2",
        kind="sweep",
        created_at="2026-05-10T14:22:33Z",
        elapsed_seconds=12.5,
        git_commit="abc123",
        git_dirty=False,
        data_range=DateRange(start="2024-01-02", end="2026-05-09"),
        symbols=["000001.SZ"],
        config_hash="a3f1c2",
        config_path="config.json",
        artifacts=[ArtifactRef(name="results", path="results.parquet", rows=42)],
    )
    payload = manifest.to_dict()
    assert payload["run_id"] == manifest.run_id
    assert payload["kind"] == "sweep"
    assert payload["data_range"] == {"start": "2024-01-02", "end": "2026-05-09"}
    assert payload["artifacts"][0]["name"] == "results"


def test_sweep_manifest_round_trip():
    manifest = SweepManifest(
        run_id="sweep-20260510-142233-a3f1c2",
        kind="sweep",
        created_at="2026-05-10T14:22:33Z",
        elapsed_seconds=1.0,
        git_commit=None,
        git_dirty=True,
        data_range=DateRange(start="2024-01-02", end="2026-05-09"),
        symbols=["000001.SZ"],
        config_hash="a3f1c2",
        config_path="config.json",
        artifacts=[],
        strategy="three-falling-buy-three-rising-sell",
        grid_size=27,
        rank_by="total_return",
        top_combos=[{"combo_id": 1, "total_return": 0.31}],
    )
    payload = manifest.to_dict()
    assert payload["strategy"] == "three-falling-buy-three-rising-sell"
    assert payload["grid_size"] == 27
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_reports_store.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement**

```python
# src/quant_backtest/reports/__init__.py
"""Backtest report artifact format and read/write helpers."""

from quant_backtest.reports.schema import (
    ArtifactRef,
    DateRange,
    ReportManifest,
    SweepManifest,
    ValidateManifest,
)

__all__ = ["ArtifactRef", "DateRange", "ReportManifest", "SweepManifest", "ValidateManifest"]
```

```python
# src/quant_backtest/reports/schema.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal


@dataclass(frozen=True)
class DateRange:
    start: str
    end: str


@dataclass(frozen=True)
class ArtifactRef:
    name: str
    path: str
    rows: int


@dataclass(frozen=True)
class ReportManifest:
    run_id: str
    kind: Literal["sweep", "validate"]
    created_at: str
    elapsed_seconds: float
    git_commit: str | None
    git_dirty: bool
    data_range: DateRange
    symbols: list[str]
    config_hash: str
    config_path: str
    artifacts: list[ArtifactRef]

    def to_dict(self) -> dict:
        return _to_serializable(self)


@dataclass(frozen=True)
class SweepManifest(ReportManifest):
    strategy: str = ""
    grid_size: int = 0
    rank_by: str = ""
    top_combos: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class ValidateManifest(ReportManifest):
    strategy: str = ""
    signal_adjust: str = "qfq"
    execution_adjust: str = "raw"
    summary_metrics: dict = field(default_factory=dict)


def _to_serializable(manifest) -> dict:
    payload = asdict(manifest)
    return payload
```

- [ ] **Step 4: Run, confirm pass**

Run: `uv run pytest tests/test_reports_store.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/reports/__init__.py src/quant_backtest/reports/schema.py tests/test_reports_store.py
git commit -m "feat(reports): manifest dataclasses for sweep and validate"
```

### Task 2.2: Reports store — write_report

**Files:**
- Create: `src/quant_backtest/reports/store.py`
- Modify: `tests/test_reports_store.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_reports_store.py`:

```python
import pandas as pd
import pytest
from pathlib import Path
from quant_backtest.reports import store


def test_write_report_creates_directory_layout(tmp_path: Path):
    config = {"strategy": "demo", "fast": 5, "slow": 20}
    artifacts = {
        "equity": pd.DataFrame({"date": pd.to_datetime(["2026-05-08"]), "equity": [1.0]}),
        "trades": pd.DataFrame({"trade_id": [1], "symbol": ["000001.SZ"]}),
    }
    run_id = store.write_report(
        kind="validate",
        config=config,
        manifest_extra={
            "strategy": "demo",
            "signal_adjust": "qfq",
            "execution_adjust": "raw",
            "summary_metrics": {"total_return": 0.05},
            "data_range": {"start": "2026-05-08", "end": "2026-05-08"},
            "symbols": ["000001.SZ"],
        },
        artifacts=artifacts,
        base_dir=tmp_path,
    )
    run_dir = tmp_path / "validations" / run_id
    assert run_dir.exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "equity.parquet").exists()
    assert (run_dir / "trades.parquet").exists()
    assert (run_dir / "config.json").exists()
    assert run_id.startswith("validate-")
    # config_hash suffix is the last 6 chars
    assert len(run_id.split("-")[-1]) == 6


def test_write_report_same_config_yields_same_hash_suffix(tmp_path):
    config = {"strategy": "demo", "fast": 5, "slow": 20}
    extras = {
        "data_range": {"start": "2026-05-08", "end": "2026-05-08"},
        "symbols": ["000001.SZ"],
    }
    a = store.write_report(kind="sweep", config=config, manifest_extra=extras, artifacts={}, base_dir=tmp_path)
    b = store.write_report(kind="sweep", config=config, manifest_extra=extras, artifacts={}, base_dir=tmp_path)
    assert a.split("-")[-1] == b.split("-")[-1]
    assert a != b  # different timestamps
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_reports_store.py -v`
Expected: FAIL — `store.write_report` missing

- [ ] **Step 3: Implement**

```python
# src/quant_backtest/reports/store.py
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from quant_backtest.reports.schema import (
    ArtifactRef,
    DateRange,
    ReportManifest,
    SweepManifest,
    ValidateManifest,
)

_KIND_TO_DIR = {"sweep": "sweeps", "validate": "validations"}


def write_report(
    *,
    kind: str,
    config: dict,
    manifest_extra: dict,
    artifacts: dict[str, pd.DataFrame],
    base_dir: Path | str = Path("reports"),
) -> str:
    if kind not in _KIND_TO_DIR:
        raise ValueError(f"unknown report kind: {kind}")
    base = Path(base_dir)
    config_hash = _hash_config(config)
    timestamp = datetime.now(tz=timezone.utc)
    run_id = f"{kind}-{timestamp.strftime('%Y%m%d-%H%M%S')}-{config_hash}"
    run_dir = base / _KIND_TO_DIR[kind] / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    artifact_refs: list[ArtifactRef] = []
    for name, df in artifacts.items():
        path = f"{name}.parquet"
        df.to_parquet(run_dir / path, index=False)
        artifact_refs.append(ArtifactRef(name=name, path=path, rows=len(df)))

    (run_dir / "config.json").write_text(json.dumps(config, indent=2, default=str))

    git_commit, git_dirty = _git_state()
    common = dict(
        run_id=run_id,
        kind=kind,
        created_at=timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        elapsed_seconds=float(manifest_extra.pop("elapsed_seconds", 0.0)),
        git_commit=git_commit,
        git_dirty=git_dirty,
        data_range=DateRange(**manifest_extra.pop("data_range")),
        symbols=list(manifest_extra.pop("symbols", [])),
        config_hash=config_hash,
        config_path="config.json",
        artifacts=artifact_refs,
    )

    if kind == "sweep":
        manifest = SweepManifest(**common, **manifest_extra)
    else:
        manifest = ValidateManifest(**common, **manifest_extra)

    (run_dir / "manifest.json").write_text(
        json.dumps(manifest.to_dict(), indent=2, default=str)
    )
    return run_id


def _hash_config(config: dict) -> str:
    blob = json.dumps(config, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:6]


def _git_state() -> tuple[str | None, bool]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, False
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return commit, False
    return commit, bool(status.strip())
```

- [ ] **Step 4: Run, confirm pass**

Run: `uv run pytest tests/test_reports_store.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/reports/store.py tests/test_reports_store.py
git commit -m "feat(reports): write_report with manifest, parquet artifacts, git provenance"
```

### Task 2.3: Reports store — list_reports / load_report / load_artifact

**Files:**
- Modify: `src/quant_backtest/reports/store.py`
- Modify: `tests/test_reports_store.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_list_and_load_round_trip(tmp_path: Path):
    config = {"strategy": "demo", "fast": 5}
    artifacts = {"results": pd.DataFrame({"combo_id": [1, 2], "total_return": [0.1, 0.2]})}
    run_id = store.write_report(
        kind="sweep",
        config=config,
        manifest_extra={
            "strategy": "demo",
            "grid_size": 2,
            "rank_by": "total_return",
            "top_combos": [{"combo_id": 1, "total_return": 0.1}],
            "data_range": {"start": "2026-05-08", "end": "2026-05-08"},
            "symbols": ["000001.SZ"],
        },
        artifacts=artifacts,
        base_dir=tmp_path,
    )
    listing = store.list_reports(tmp_path, kind="sweep")
    assert len(listing) == 1
    assert listing[0].run_id == run_id
    loaded = store.load_report(tmp_path, run_id)
    assert loaded.run_id == run_id
    df = store.load_artifact(tmp_path, run_id, "results")
    assert list(df.columns) == ["combo_id", "total_return"]
    assert len(df) == 2


def test_list_reports_filters_by_since(tmp_path: Path):
    from datetime import date as _date
    listing = store.list_reports(tmp_path, since=_date(2099, 1, 1))
    assert listing == []
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_reports_store.py -v`
Expected: FAIL — `list_reports` missing

- [ ] **Step 3: Implement**

Append to `src/quant_backtest/reports/store.py`:

```python
from datetime import date as _date


def list_reports(
    base_dir: Path | str,
    *,
    kind: str | None = None,
    since: _date | None = None,
    limit: int | None = None,
) -> list[ReportManifest]:
    base = Path(base_dir)
    kinds = [kind] if kind else list(_KIND_TO_DIR.keys())
    manifests: list[ReportManifest] = []
    for k in kinds:
        sub = base / _KIND_TO_DIR[k]
        if not sub.exists():
            continue
        for run_dir in sub.iterdir():
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            manifests.append(_load_manifest_from_dict(json.loads(manifest_path.read_text())))
    manifests.sort(key=lambda m: m.created_at, reverse=True)
    if since is not None:
        manifests = [m for m in manifests if m.created_at[:10] >= since.isoformat()]
    if limit is not None:
        manifests = manifests[:limit]
    return manifests


def load_report(base_dir: Path | str, run_id: str) -> ReportManifest:
    base = Path(base_dir)
    kind = run_id.split("-", 1)[0]
    if kind not in _KIND_TO_DIR:
        raise FileNotFoundError(run_id)
    manifest_path = base / _KIND_TO_DIR[kind] / run_id / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(run_id)
    return _load_manifest_from_dict(json.loads(manifest_path.read_text()))


def load_artifact(base_dir: Path | str, run_id: str, name: str) -> pd.DataFrame:
    base = Path(base_dir)
    kind = run_id.split("-", 1)[0]
    path = base / _KIND_TO_DIR[kind] / run_id / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{run_id}/{name}")
    return pd.read_parquet(path)


def _load_manifest_from_dict(payload: dict) -> ReportManifest:
    payload = dict(payload)
    payload["data_range"] = DateRange(**payload["data_range"])
    payload["artifacts"] = [ArtifactRef(**a) for a in payload.get("artifacts", [])]
    if payload["kind"] == "sweep":
        return SweepManifest(**payload)
    if payload["kind"] == "validate":
        return ValidateManifest(**payload)
    return ReportManifest(**payload)
```

- [ ] **Step 4: Run, confirm pass**

Run: `uv run pytest tests/test_reports_store.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/reports/store.py tests/test_reports_store.py
git commit -m "feat(reports): list_reports / load_report / load_artifact"
```

### Task 2.4: CLI — sweep writes report

**Files:**
- Modify: `src/quant_backtest/cli_backtest.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli.py` (use existing patterns; if the file uses `subprocess` or in-process `main()`, follow that style):

```python
def test_sweep_writes_report_by_default(tmp_path, monkeypatch, populated_cache_root):
    """After running quant-backtest sweep, a report should appear under reports/sweeps."""
    monkeypatch.chdir(tmp_path)
    # invoke sweep main() with minimal args that match the existing test fixtures
    from quant_backtest.cli_backtest import main as sweep_main
    import sys
    sys.argv = [
        "quant-backtest", "sweep",
        "--cache-root", str(populated_cache_root),
        "--symbols", "000001.SZ",
        "--strategy", "three-falling-buy-three-rising-sell",
        "--signal-counts", "2",
    ]
    sweep_main()
    sweeps_dir = tmp_path / "reports" / "sweeps"
    assert sweeps_dir.exists()
    assert any(d.is_dir() for d in sweeps_dir.iterdir())


def test_sweep_no_report_flag_skips_write(tmp_path, monkeypatch, populated_cache_root):
    monkeypatch.chdir(tmp_path)
    from quant_backtest.cli_backtest import main as sweep_main
    import sys
    sys.argv = [
        "quant-backtest", "sweep",
        "--cache-root", str(populated_cache_root),
        "--symbols", "000001.SZ",
        "--strategy", "three-falling-buy-three-rising-sell",
        "--signal-counts", "2",
        "--no-report",
    ]
    sweep_main()
    sweeps_dir = tmp_path / "reports" / "sweeps"
    assert not sweeps_dir.exists()
```

If `tests/test_cli.py` doesn't already provide a `populated_cache_root` fixture, copy/adapt one from `tests/conftest.py`. The point is a cache with one symbol that supports a trivial sweep.

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_cli.py::test_sweep_writes_report_by_default -v`
Expected: FAIL — either `--no-report` unrecognized or no `reports/` produced

- [ ] **Step 3: Modify cli_backtest.py — add `--no-report` and call `write_report` after sweep**

In the sweep subparser, add:

```python
sweep.add_argument("--no-report", action="store_true",
                   help="Do not write the run to reports/sweeps/")
```

After the sweep grid completes (locate the line that prints/returns the result table), append a write block:

```python
from quant_backtest.reports.store import write_report
import time

if not getattr(args, "no_report", False):
    elapsed = time.perf_counter() - sweep_started_at  # capture sweep_started_at = time.perf_counter() before the run
    artifacts = {"results": results_frame}  # the existing sweep result DataFrame
    write_report(
        kind="sweep",
        config=_sweep_config_dict(args),  # build a dict from argparse Namespace
        manifest_extra={
            "elapsed_seconds": elapsed,
            "data_range": {"start": str(start_date), "end": str(end_date)},
            "symbols": list(symbols),
            "strategy": args.strategy,
            "grid_size": int(len(results_frame)),
            "rank_by": args.rank_by,
            "top_combos": results_frame.head(5).to_dict(orient="records"),
        },
        artifacts=artifacts,
    )
```

Add a `_sweep_config_dict(args)` helper in the same file that produces a json-serializable dict from the argparse namespace (filter out `--no-report` and `--cache-root`).

- [ ] **Step 4: Run all CLI tests**

Run: `uv run pytest tests/test_cli.py -v`
Expected: previously passing tests still pass + the two new tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/cli_backtest.py tests/test_cli.py
git commit -m "feat(cli): sweep writes report by default; --no-report opts out"
```

### Task 2.5: CLI — validate writes report

**Files:**
- Modify: `src/quant_backtest/cli_backtest.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
def test_validate_writes_report_with_equity_and_trades(tmp_path, monkeypatch, populated_cache_root):
    monkeypatch.chdir(tmp_path)
    from quant_backtest.cli_backtest import main as backtest_main
    import sys
    sys.argv = [
        "quant-backtest", "validate",
        "--cache-root", str(populated_cache_root),
        "--symbols", "000001.SZ",
        "--signal-adjust", "qfq",
        "--execution-adjust", "raw",
        "--fast-period", "5",
        "--slow-period", "20",
    ]
    backtest_main()
    val_dir = tmp_path / "reports" / "validations"
    assert val_dir.exists()
    runs = list(val_dir.iterdir())
    assert len(runs) == 1
    assert (runs[0] / "equity.parquet").exists()
    assert (runs[0] / "trades.parquet").exists()
    assert (runs[0] / "manifest.json").exists()
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_cli.py::test_validate_writes_report_with_equity_and_trades -v`
Expected: FAIL — `reports/validations/` not created

- [ ] **Step 3: Modify validate path**

Add `validate.add_argument("--no-report", action="store_true")` to the validate subparser.

After the backtrader engine finishes, extract:
- `equity_df` from the `Equity` analyzer (or the engine result; if not exposed, add a minimal helper to convert backtrader's broker value series to a DataFrame with `date, cash, position_value, equity, drawdown`)
- `trades_df` from the trade analyzer (existing analyzers expose this; if not, an empty DataFrame is acceptable for v1 as long as the file is written)
- `summary_metrics` dict from the existing summary printout

Call:

```python
write_report(
    kind="validate",
    config=_validate_config_dict(args),
    manifest_extra={
        "elapsed_seconds": elapsed,
        "data_range": {"start": str(start_date), "end": str(end_date)},
        "symbols": list(symbols),
        "strategy": args.strategy or "signal-sma-cross",
        "signal_adjust": args.signal_adjust,
        "execution_adjust": args.execution_adjust,
        "summary_metrics": summary_metrics,
    },
    artifacts={"equity": equity_df, "trades": trades_df},
)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/cli_backtest.py tests/test_cli.py
git commit -m "feat(cli): validate writes report with equity, trades, summary metrics"
```

---

## Phase 3 — FastAPI Skeleton + Data Routes

### Task 3.1: Add `api` extra and entrypoint

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Edit pyproject.toml**

Add to `[project.optional-dependencies]`:

```toml
api = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "sse-starlette>=2.1",
    "httpx>=0.27",  # for tests
]
```

Append `"fastapi>=0.115", "uvicorn[standard]>=0.32", "sse-starlette>=2.1", "httpx>=0.27"` to the `all` and `test` extras as well.

Add to `[project.scripts]`:

```toml
quant-api = "quant_backtest.api.app:run"
```

- [ ] **Step 2: Sync deps**

Run: `uv sync --extra api --extra test`
Expected: lock updates succeed; `uv pip show fastapi` confirms install.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add api optional extra (fastapi, uvicorn, sse-starlette)"
```

### Task 3.2: API skeleton — app, errors, health

**Files:**
- Create: `src/quant_backtest/api/__init__.py`
- Create: `src/quant_backtest/api/app.py`
- Create: `src/quant_backtest/api/errors.py`
- Create: `src/quant_backtest/api/deps.py`
- Create: `src/quant_backtest/api/routers/__init__.py`
- Create: `src/quant_backtest/api/routers/system.py`
- Create: `tests/test_api_health.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_health.py
from fastapi.testclient import TestClient

from quant_backtest.api.app import create_app


def test_health_returns_ok(tmp_path):
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"


def test_404_returns_rfc7807_envelope(tmp_path):
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    client = TestClient(app)
    response = client.get("/api/no-such-route")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_api_health.py -v`
Expected: FAIL — `create_app` not found

- [ ] **Step 3: Implement**

```python
# src/quant_backtest/api/__init__.py
"""FastAPI HTTP layer for Muce."""
```

```python
# src/quant_backtest/api/errors.py
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _envelope(code: str, message: str, status_code: int, details: dict | None = None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        return _envelope(
            code=f"http_{exc.status_code}",
            message=str(exc.detail) if exc.detail else "HTTP error",
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(request: Request, exc: RequestValidationError):
        return _envelope(
            code="validation_error",
            message="Request validation failed",
            status_code=422,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _internal_exc(request: Request, exc: Exception):
        return _envelope(
            code="internal_error",
            message=str(exc),
            status_code=500,
        )
```

```python
# src/quant_backtest/api/deps.py
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

from quant_backtest.data.cache import ParquetCache


def get_cache(request: Request) -> ParquetCache:
    return request.app.state.cache


def get_reports_dir(request: Request) -> Path:
    return request.app.state.reports_dir


CacheDep = Annotated[ParquetCache, Depends(get_cache)]
ReportsDirDep = Annotated[Path, Depends(get_reports_dir)]
```

```python
# src/quant_backtest/api/routers/__init__.py
```

```python
# src/quant_backtest/api/routers/system.py
from __future__ import annotations

from fastapi import APIRouter

from quant_backtest.api.deps import CacheDep, ReportsDirDep

router = APIRouter()


@router.get("/health")
def health(cache: CacheDep, reports_dir: ReportsDirDep) -> dict:
    return {
        "data": {
            "status": "ok",
            "cache_root_exists": cache.root.exists() if hasattr(cache, "root") else True,
            "reports_dir_exists": reports_dir.exists(),
        },
        "meta": {},
    }


@router.get("/version")
def version() -> dict:
    from importlib.metadata import version as _version
    try:
        v = _version("muce")
    except Exception:
        v = "0.0.0"
    return {"data": {"version": v, "provider": "baostock"}, "meta": {}}
```

```python
# src/quant_backtest/api/app.py
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from quant_backtest.api.errors import install_error_handlers
from quant_backtest.api.routers import system as system_router
from quant_backtest.data.cache import ParquetCache


def create_app(
    *,
    cache_root: Path | str | None = None,
    reports_dir: Path | str | None = None,
) -> FastAPI:
    cache_root = Path(cache_root or os.environ.get("MUCE_CACHE_ROOT", "data/cache/a_share/daily"))
    reports_dir = Path(reports_dir or os.environ.get("MUCE_REPORTS_DIR", "reports"))

    app = FastAPI(title="Muce API", version="0.1.0")
    app.state.cache = ParquetCache(cache_root)
    app.state.reports_dir = reports_dir

    install_error_handlers(app)
    app.include_router(system_router.router, prefix="/api")
    return app


app = create_app()


def run() -> None:
    """Console-script entrypoint for `quant-api`."""
    import uvicorn
    uvicorn.run(
        "quant_backtest.api.app:app",
        host=os.environ.get("MUCE_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("MUCE_API_PORT", "8000")),
        reload=bool(os.environ.get("MUCE_API_RELOAD", "")),
    )
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_api_health.py -v`
Expected: 2 passed

- [ ] **Step 5: Smoke-test the server**

Run: `uv run quant-api` in one terminal; `curl http://127.0.0.1:8000/api/health` in another.
Expected: `{"data":{"status":"ok",...},"meta":{}}`. Stop with Ctrl-C.

- [ ] **Step 6: Commit**

```bash
git add src/quant_backtest/api tests/test_api_health.py
git commit -m "feat(api): FastAPI skeleton with health, version, RFC 7807 errors"
```

### Task 3.3: Data router — symbols, bars, coverage

**Files:**
- Create: `src/quant_backtest/api/schemas.py`
- Create: `src/quant_backtest/api/routers/data.py`
- Create: `tests/test_api_data.py`
- Modify: `src/quant_backtest/api/app.py` (mount router)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_data.py
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from quant_backtest.api.app import create_app
from quant_backtest.data.cache import ParquetCache


@pytest.fixture()
def client(tmp_path) -> TestClient:
    cache = ParquetCache(tmp_path / "cache")
    frame = pd.DataFrame({
        "symbol": ["000001.SZ"] * 3 + ["600000.SH"] * 2,
        "date": pd.to_datetime(["2026-05-07","2026-05-08","2026-05-09","2026-05-08","2026-05-09"]),
        "open":   [10.0, 10.5, 10.8, 8.0, 8.2],
        "high":   [10.6, 11.0, 11.0, 8.4, 8.5],
        "low":    [9.9, 10.3, 10.6, 7.9, 8.0],
        "close":  [10.5, 10.8, 10.9, 8.2, 8.4],
        "volume": [1_000_000, 1_100_000, 950_000, 800_000, 750_000],
        "turnover":[1.0e7, 1.1e7, 1.0e7, 6.5e6, 6.3e6],
        "source": ["baostock"] * 5,
        "adjust": ["qfq"] * 5,
    })
    cache.write(frame)
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    return TestClient(app)


def test_list_symbols(client):
    response = client.get("/api/symbols")
    assert response.status_code == 200
    symbols = [s["symbol"] for s in response.json()["data"]]
    assert set(symbols) == {"000001.SZ", "600000.SH"}


def test_symbol_info(client):
    response = client.get("/api/symbols/000001.SZ")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["symbol"] == "000001.SZ"
    assert body["market"] == "SZ"
    assert body["last_cached_date"] == "2026-05-09"


def test_bars(client):
    response = client.get("/api/bars/000001.SZ?adjust=qfq")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["symbol"] == "000001.SZ"
    assert len(body["rows"]) == 3
    assert body["rows"][0]["date"] == "2026-05-07"


def test_cache_coverage(client):
    response = client.get("/api/cache/coverage")
    assert response.status_code == 200
    coverage = {entry["symbol"]: entry for entry in response.json()["data"]}
    assert coverage["000001.SZ"]["rows"] == 3
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_api_data.py -v`
Expected: FAIL — 404 on `/api/symbols`

- [ ] **Step 3: Implement schemas + router**

```python
# src/quant_backtest/api/schemas.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Envelope(BaseModel):
    data: Any
    meta: dict = {}
```

```python
# src/quant_backtest/api/routers/data.py
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from quant_backtest.api.deps import CacheDep
from quant_backtest.services import data_service

router = APIRouter()


@router.get("/symbols")
def list_symbols(
    cache: CacheDep,
    q: str | None = None,
    market: str | None = None,
    adjust: str = "qfq",
    limit: int | None = None,
    offset: int = 0,
):
    rows = data_service.list_symbols(cache, adjust=adjust, query=q, market=market, limit=limit, offset=offset)
    payload = [
        {
            "symbol": r.symbol,
            "market": r.market,
            "last_cached_date": str(r.last_cached_date) if r.last_cached_date else None,
        }
        for r in rows
    ]
    return {"data": payload, "meta": {"count": len(payload)}}


@router.get("/symbols/{symbol}")
def symbol_info(symbol: str, cache: CacheDep, adjust: str = "qfq"):
    info = data_service.symbol_info(cache, symbol, adjust=adjust)
    if info.last_cached_date is None:
        raise HTTPException(status_code=404, detail=f"symbol not in cache: {symbol}")
    return {
        "data": {
            "symbol": info.symbol,
            "market": info.market,
            "last_cached_date": str(info.last_cached_date),
        },
        "meta": {},
    }


@router.get("/bars/{symbol}")
def bars(
    symbol: str,
    cache: CacheDep,
    adjust: str = "qfq",
    start: date | None = None,
    end: date | None = None,
    indicators: str = "",
):
    indicator_tuple = tuple(filter(None, indicators.split(",")))
    result = data_service.load_bars_with_indicators(
        cache, symbol, adjust=adjust, start=start, end=end, indicators=indicator_tuple,
    )
    return {
        "data": {
            "symbol": result.symbol,
            "adjust": result.adjust,
            "indicators_requested": list(result.indicators_requested),
            "rows": result.rows,
        },
        "meta": {"rows": len(result.rows)},
    }


@router.get("/cache/coverage")
def cache_coverage(cache: CacheDep, adjust: str = "qfq"):
    entries = data_service.cache_coverage(cache, adjust=adjust)
    return {
        "data": [
            {
                "symbol": e.symbol,
                "rows": e.rows,
                "first_date": str(e.first_date) if e.first_date else None,
                "last_date": str(e.last_date) if e.last_date else None,
            }
            for e in entries
        ],
        "meta": {"count": len(entries)},
    }
```

- [ ] **Step 4: Mount router in app.py**

Edit `src/quant_backtest/api/app.py`:

```python
from quant_backtest.api.routers import data as data_router
# ...inside create_app, after install_error_handlers:
app.include_router(data_router.router, prefix="/api")
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_api_data.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/quant_backtest/api/schemas.py src/quant_backtest/api/routers/data.py src/quant_backtest/api/app.py tests/test_api_data.py
git commit -m "feat(api): data router (symbols, bars, cache coverage)"
```

---

## Phase 4 — Reports Router

### Task 4.1: Reports service

**Files:**
- Create: `src/quant_backtest/services/reports_service.py`

- [ ] **Step 1: Implement (thin wrapper around store)**

```python
# src/quant_backtest/services/reports_service.py
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from quant_backtest.reports import store
from quant_backtest.reports.schema import ReportManifest


def list_reports(
    base_dir: Path,
    *,
    kind: str | None = None,
    since: date | None = None,
    limit: int | None = None,
) -> list[ReportManifest]:
    return store.list_reports(base_dir, kind=kind, since=since, limit=limit)


def load_report(base_dir: Path, run_id: str) -> ReportManifest:
    return store.load_report(base_dir, run_id)


def load_artifact(base_dir: Path, run_id: str, name: str) -> pd.DataFrame:
    return store.load_artifact(base_dir, run_id, name)
```

- [ ] **Step 2: Quick smoke**

Run: `uv run python -c "from quant_backtest.services import reports_service; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/quant_backtest/services/reports_service.py
git commit -m "feat(services): reports_service wrapper"
```

### Task 4.2: Reports router

**Files:**
- Create: `src/quant_backtest/api/routers/reports.py`
- Create: `tests/test_api_reports.py`
- Modify: `src/quant_backtest/api/app.py` (mount)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_reports.py
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from quant_backtest.api.app import create_app
from quant_backtest.reports.store import write_report


@pytest.fixture()
def client_with_reports(tmp_path) -> TestClient:
    reports_dir = tmp_path / "reports"
    write_report(
        kind="sweep",
        config={"strategy": "demo", "fast": 5},
        manifest_extra={
            "elapsed_seconds": 1.2,
            "data_range": {"start": "2026-05-08", "end": "2026-05-09"},
            "symbols": ["000001.SZ"],
            "strategy": "demo",
            "grid_size": 2,
            "rank_by": "total_return",
            "top_combos": [{"combo_id": 1, "total_return": 0.1}],
        },
        artifacts={"results": pd.DataFrame({"combo_id": [1, 2], "total_return": [0.1, 0.2]})},
        base_dir=reports_dir,
    )
    write_report(
        kind="validate",
        config={"strategy": "validate-demo", "fast": 5, "slow": 20},
        manifest_extra={
            "elapsed_seconds": 3.4,
            "data_range": {"start": "2026-05-08", "end": "2026-05-09"},
            "symbols": ["000001.SZ"],
            "strategy": "validate-demo",
            "signal_adjust": "qfq",
            "execution_adjust": "raw",
            "summary_metrics": {"total_return": 0.05, "sharpe": 0.8, "max_drawdown": -0.02, "trades": 3},
        },
        artifacts={
            "equity": pd.DataFrame({"date": pd.to_datetime(["2026-05-08","2026-05-09"]),
                                    "equity": [1.0, 1.05]}),
            "trades": pd.DataFrame({"trade_id": [1], "symbol": ["000001.SZ"], "pnl": [0.05]}),
        },
        base_dir=reports_dir,
    )
    app = create_app(cache_root=tmp_path / "cache", reports_dir=reports_dir)
    return TestClient(app)


def test_list_reports(client_with_reports):
    response = client_with_reports.get("/api/reports")
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    kinds = {item["kind"] for item in items}
    assert kinds == {"sweep", "validate"}


def test_list_reports_filtered_by_kind(client_with_reports):
    response = client_with_reports.get("/api/reports?kind=sweep")
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["kind"] == "sweep"


def test_load_report_detail(client_with_reports):
    listing = client_with_reports.get("/api/reports?kind=validate").json()["data"]
    run_id = listing[0]["run_id"]
    detail = client_with_reports.get(f"/api/reports/{run_id}")
    assert detail.status_code == 200
    body = detail.json()["data"]
    assert body["run_id"] == run_id
    assert body["summary_metrics"]["total_return"] == 0.05


def test_load_validate_artifacts(client_with_reports):
    listing = client_with_reports.get("/api/reports?kind=validate").json()["data"]
    run_id = listing[0]["run_id"]
    equity = client_with_reports.get(f"/api/reports/{run_id}/equity").json()["data"]
    assert len(equity["rows"]) == 2
    trades = client_with_reports.get(f"/api/reports/{run_id}/trades").json()["data"]
    assert len(trades["rows"]) == 1


def test_404_for_unknown_run_id(client_with_reports):
    response = client_with_reports.get("/api/reports/sweep-19990101-000000-000000")
    assert response.status_code == 404
    assert "error" in response.json()
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_api_reports.py -v`
Expected: FAIL — 404 across the board

- [ ] **Step 3: Implement router**

```python
# src/quant_backtest/api/routers/reports.py
from __future__ import annotations

from dataclasses import asdict
from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException

from quant_backtest.api.deps import ReportsDirDep
from quant_backtest.services import reports_service

router = APIRouter()


@router.get("")
def list_reports(
    reports_dir: ReportsDirDep,
    kind: str | None = None,
    since: date | None = None,
    limit: int | None = None,
):
    items = reports_service.list_reports(reports_dir, kind=kind, since=since, limit=limit)
    return {"data": [_manifest_to_dict(m) for m in items], "meta": {"count": len(items)}}


@router.get("/{run_id}")
def get_report(run_id: str, reports_dir: ReportsDirDep):
    try:
        manifest = reports_service.load_report(reports_dir, run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"report not found: {run_id}")
    return {"data": _manifest_to_dict(manifest), "meta": {}}


@router.get("/{run_id}/equity")
def get_equity(run_id: str, reports_dir: ReportsDirDep):
    return _artifact_response(reports_dir, run_id, "equity")


@router.get("/{run_id}/trades")
def get_trades(run_id: str, reports_dir: ReportsDirDep):
    return _artifact_response(reports_dir, run_id, "trades")


@router.get("/{run_id}/sweep")
def get_sweep(run_id: str, reports_dir: ReportsDirDep):
    return _artifact_response(reports_dir, run_id, "results")


def _artifact_response(reports_dir, run_id: str, name: str):
    try:
        df = reports_service.load_artifact(reports_dir, run_id, name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"artifact not found: {run_id}/{name}")
    rows = []
    for record in df.to_dict(orient="records"):
        for k, v in list(record.items()):
            if isinstance(v, pd.Timestamp):
                record[k] = v.strftime("%Y-%m-%d")
        rows.append(record)
    return {"data": {"name": name, "rows": rows}, "meta": {"rows": len(rows)}}


def _manifest_to_dict(manifest) -> dict:
    return manifest.to_dict()
```

- [ ] **Step 4: Mount router**

Edit `src/quant_backtest/api/app.py`:

```python
from quant_backtest.api.routers import reports as reports_router
# inside create_app:
app.include_router(reports_router.router, prefix="/api/reports")
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_api_reports.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/quant_backtest/api/routers/reports.py src/quant_backtest/api/app.py tests/test_api_reports.py
git commit -m "feat(api): reports router (list, detail, equity/trades/sweep artifacts)"
```

---

## Phase 5 — Selection Router + Job Progress (SSE)

### Task 5.1: JobRegistry

**Files:**
- Create: `src/quant_backtest/api/jobs.py`
- Create: `tests/test_api_selection.py` (just for JobRegistry first)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_selection.py
from __future__ import annotations

import time

import pytest

from quant_backtest.api.jobs import JobRegistry, JobState


def test_job_registry_lifecycle():
    registry = JobRegistry(ttl_seconds=60)
    job_id = registry.create_job()
    state = registry.get(job_id)
    assert state.status == "pending"

    registry.update(job_id, status="running", stage="load_panel", progress=0.1, message="...")
    assert registry.get(job_id).stage == "load_panel"

    registry.complete(job_id, result={"candidates": []})
    final = registry.get(job_id)
    assert final.status == "done"
    assert final.result == {"candidates": []}


def test_job_registry_records_failure():
    registry = JobRegistry(ttl_seconds=60)
    job_id = registry.create_job()
    registry.fail(job_id, error="boom")
    state = registry.get(job_id)
    assert state.status == "failed"
    assert state.error == "boom"


def test_job_registry_purges_expired():
    registry = JobRegistry(ttl_seconds=0)
    job_id = registry.create_job()
    registry.complete(job_id, result={})
    time.sleep(0.01)
    registry.purge_expired()
    with pytest.raises(KeyError):
        registry.get(job_id)
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_api_selection.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement**

```python
# src/quant_backtest/api/jobs.py
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class JobState:
    job_id: str
    status: str = "pending"  # pending | running | done | failed
    stage: str | None = None
    progress: float = 0.0
    message: str = ""
    result: Any | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class JobRegistry:
    def __init__(self, *, ttl_seconds: int = 3600) -> None:
        self._jobs: dict[str, JobState] = {}
        self._events: dict[str, asyncio.Event] = {}
        self._lock = Lock()
        self._ttl = ttl_seconds

    def create_job(self) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = JobState(job_id=job_id)
            self._events[job_id] = asyncio.Event()
        return job_id

    def get(self, job_id: str) -> JobState:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id]

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            state = self._jobs[job_id]
            for k, v in fields.items():
                setattr(state, k, v)
            state.updated_at = time.time()
            event = self._events.get(job_id)
        if event is not None:
            event.set()

    def complete(self, job_id: str, *, result: Any) -> None:
        self.update(job_id, status="done", progress=1.0, stage="done", result=result, message="完成")

    def fail(self, job_id: str, *, error: str) -> None:
        self.update(job_id, status="failed", error=error, message=error)

    def purge_expired(self) -> None:
        cutoff = time.time() - self._ttl
        with self._lock:
            expired = [jid for jid, s in self._jobs.items() if s.updated_at < cutoff and s.status in {"done", "failed"}]
            for jid in expired:
                self._jobs.pop(jid, None)
                self._events.pop(jid, None)

    def event(self, job_id: str) -> asyncio.Event:
        with self._lock:
            return self._events[job_id]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_api_selection.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/api/jobs.py tests/test_api_selection.py
git commit -m "feat(api): in-process JobRegistry with TTL purge"
```

### Task 5.2: Selection router — submit + poll

**Files:**
- Create: `src/quant_backtest/api/routers/selection.py`
- Modify: `src/quant_backtest/api/app.py` (mount + create JobRegistry on app.state)
- Modify: `tests/test_api_selection.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_api_selection.py`:

```python
import pandas as pd
from fastapi.testclient import TestClient
from quant_backtest.api.app import create_app
from quant_backtest.data.cache import ParquetCache


@pytest.fixture()
def client_with_cache(tmp_path) -> TestClient:
    cache = ParquetCache(tmp_path / "cache")
    dates = pd.bdate_range("2026-01-01", periods=80)
    closes = [10.0 + i * 0.1 for i in range(80)]
    frame = pd.DataFrame({
        "symbol": ["000001.SZ"] * 80,
        "date": dates,
        "open": closes,
        "high": [c + 0.2 for c in closes],
        "low":  [c - 0.2 for c in closes],
        "close": closes,
        "volume": [1_000_000] * 80,
        "turnover": [c * 1_000_000 for c in closes],
        "source": ["baostock"] * 80,
        "adjust": ["qfq"] * 80,
    })
    cache.write(frame)
    app = create_app(cache_root=tmp_path / "cache", reports_dir=tmp_path / "reports")
    return TestClient(app)


def test_factors_listing(client_with_cache):
    response = client_with_cache.get("/api/selection/factors")
    assert response.status_code == 200
    keys = {f["key"] for f in response.json()["data"]}
    assert {"ma_breakout", "rsi_momentum", "macd_golden_cross"} <= keys


def test_defaults_listing(client_with_cache):
    response = client_with_cache.get("/api/selection/defaults")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["min_score"] == 2  # FactorSelectorConfig default
    assert body["top_n"] == 20


def test_selection_job_lifecycle(client_with_cache):
    response = client_with_cache.post(
        "/api/selection/jobs",
        json={"as_of_date": None, "config": {"min_score": 0, "top_n": 5}, "symbol_universe": None},
    )
    assert response.status_code == 200
    job_id = response.json()["data"]["job_id"]

    # poll until done
    import time
    for _ in range(50):
        state = client_with_cache.get(f"/api/selection/jobs/{job_id}").json()["data"]
        if state["status"] == "done":
            break
        time.sleep(0.1)
    else:
        pytest.fail("job did not complete in time")

    assert state["status"] == "done"
    assert "candidates" in state["result"]
    assert "summary" in state["result"]
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_api_selection.py -v`
Expected: FAIL — `/api/selection/factors` 404

- [ ] **Step 3: Implement router**

```python
# src/quant_backtest/api/routers/selection.py
from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from quant_backtest.api.deps import CacheDep
from quant_backtest.api.jobs import JobRegistry, JobState
from quant_backtest.selection import FactorSelectorConfig
from quant_backtest.selection.factors import FACTOR_COLUMNS
from quant_backtest.services import selection_service

router = APIRouter()


_FACTOR_DESCRIPTIONS = {
    "ma_breakout": "均线突破：收盘价站上长期均线",
    "kdj_golden_cross": "KDJ 金叉",
    "macd_golden_cross": "MACD 金叉",
    "rsi_momentum": "RSI 动量：高于阈值",
    "volume_breakout": "成交量放量",
    "boll_breakout": "布林带突破上轨",
}


class SelectionRequest(BaseModel):
    as_of_date: str | None = None
    config: dict = Field(default_factory=dict)
    symbol_universe: list[str] | None = None


def get_registry(request: Request) -> JobRegistry:
    return request.app.state.job_registry


RegistryDep = Annotated[JobRegistry, Depends(get_registry)]


@router.get("/factors")
def list_factors():
    payload = [
        {"key": key, "name_cn": _FACTOR_DESCRIPTIONS.get(key, key), "description": _FACTOR_DESCRIPTIONS.get(key, "")}
        for key in FACTOR_COLUMNS
    ]
    return {"data": payload, "meta": {"count": len(payload)}}


@router.get("/defaults")
def defaults():
    cfg = FactorSelectorConfig()
    payload = asdict(cfg)
    payload["require_factors"] = list(cfg.require_factors)
    payload["exclude_factors"] = list(cfg.exclude_factors)
    return {"data": payload, "meta": {}}


@router.post("/jobs")
async def submit_job(req: SelectionRequest, cache: CacheDep, registry: RegistryDep):
    config = _build_config(req.config)
    job_id = registry.create_job()

    async def _run():
        loop = asyncio.get_running_loop()

        def progress_cb(stage, value, message):
            registry.update(job_id, status="running", stage=stage, progress=value, message=message)

        def _do():
            return selection_service.run_selection(
                cache=cache,
                config=config,
                as_of_date=req.as_of_date,
                symbols=req.symbol_universe,
                on_progress=progress_cb,
            )

        try:
            result = await asyncio.wait_for(loop.run_in_executor(None, _do), timeout=30.0)
            registry.complete(job_id, result={
                "as_of_date": result.as_of_date,
                "config": result.config,
                "candidates": result.candidates,
                "summary": result.summary,
            })
        except asyncio.TimeoutError:
            registry.fail(job_id, error="选股超时（>30s），建议改用 CLI")
        except Exception as exc:
            registry.fail(job_id, error=f"{type(exc).__name__}: {exc}")

    asyncio.create_task(_run())
    return {"data": {"job_id": job_id}, "meta": {}}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, registry: RegistryDep):
    try:
        state = registry.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")
    return {"data": _state_to_dict(state), "meta": {}}


def _build_config(payload: dict) -> FactorSelectorConfig:
    fields = {}
    cfg_default = FactorSelectorConfig()
    for key, value in payload.items():
        if not hasattr(cfg_default, key):
            continue
        if key in {"require_factors", "exclude_factors"}:
            value = tuple(value or ())
        fields[key] = value
    return FactorSelectorConfig(**{**asdict(cfg_default), **fields,
                                   "require_factors": fields.get("require_factors", cfg_default.require_factors),
                                   "exclude_factors": fields.get("exclude_factors", cfg_default.exclude_factors)})


def _state_to_dict(state: JobState) -> dict:
    return {
        "job_id": state.job_id,
        "status": state.status,
        "stage": state.stage,
        "progress": state.progress,
        "message": state.message,
        "result": state.result,
        "error": state.error,
    }
```

- [ ] **Step 4: Mount router + JobRegistry on app**

Edit `src/quant_backtest/api/app.py`:

```python
from quant_backtest.api.jobs import JobRegistry
from quant_backtest.api.routers import selection as selection_router
# inside create_app:
app.state.job_registry = JobRegistry(ttl_seconds=3600)
app.include_router(selection_router.router, prefix="/api/selection")
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_api_selection.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add src/quant_backtest/api/routers/selection.py src/quant_backtest/api/app.py tests/test_api_selection.py
git commit -m "feat(api): selection router with async job submission and polling"
```

### Task 5.3: SSE stream endpoint

**Files:**
- Modify: `src/quant_backtest/api/routers/selection.py`
- Modify: `tests/test_api_selection.py`

- [ ] **Step 1: Write the failing test**

```python
def test_selection_job_stream(client_with_cache):
    submit = client_with_cache.post(
        "/api/selection/jobs",
        json={"as_of_date": None, "config": {"min_score": 0, "top_n": 5}, "symbol_universe": None},
    )
    job_id = submit.json()["data"]["job_id"]

    # Use streaming client to read SSE
    with client_with_cache.stream("GET", f"/api/selection/jobs/{job_id}/stream") as response:
        assert response.status_code == 200
        events = []
        for line in response.iter_lines():
            if line.startswith("data:"):
                payload = line.removeprefix("data:").strip()
                events.append(payload)
            if line.startswith("event: done"):
                break
            if len(events) > 50:
                break
    assert any("done" in e for e in events)
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest tests/test_api_selection.py::test_selection_job_stream -v`
Expected: FAIL — 404

- [ ] **Step 3: Implement SSE endpoint**

Append to `src/quant_backtest/api/routers/selection.py`:

```python
import json
from sse_starlette.sse import EventSourceResponse


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str, registry: RegistryDep):
    try:
        registry.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")

    async def event_generator():
        last_seen = (None, -1.0)
        while True:
            try:
                state = registry.get(job_id)
            except KeyError:
                yield {"event": "error", "data": json.dumps({"message": "job purged"})}
                return
            current = (state.stage, state.progress)
            if current != last_seen:
                last_seen = current
                event_name = "progress"
                payload = {
                    "stage": state.stage,
                    "progress": state.progress,
                    "message": state.message,
                }
                if state.status == "done":
                    event_name = "done"
                    payload["result"] = state.result
                if state.status == "failed":
                    event_name = "failed"
                    payload["error"] = state.error
                yield {"event": event_name, "data": json.dumps(payload, default=str)}
                if state.status in {"done", "failed"}:
                    return
            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_api_selection.py -v`
Expected: 7 passed

- [ ] **Step 5: Smoke-test from terminal**

Run: `uv run quant-api &` ; then:
```bash
curl -s -X POST http://127.0.0.1:8000/api/selection/jobs \
  -H 'content-type: application/json' \
  -d '{"as_of_date":null,"config":{"min_score":0,"top_n":5},"symbol_universe":null}' \
  | jq -r .data.job_id | xargs -I{} curl -N http://127.0.0.1:8000/api/selection/jobs/{}/stream
```
Expected: a sequence of `event: progress` lines then `event: done`.

- [ ] **Step 6: Commit**

```bash
git add src/quant_backtest/api/routers/selection.py tests/test_api_selection.py
git commit -m "feat(api): SSE stream for selection job progress"
```

---

## Phase 6 — Polish

### Task 6.1: Result caching for selection

**Files:**
- Modify: `src/quant_backtest/services/selection_service.py`
- Modify: `tests/test_services_selection.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_selection_caches_repeated_calls(populated_cache):
    config = FactorSelectorConfig(min_score=0, top_n=5)
    a = selection_service.run_selection(
        cache=populated_cache, config=config, as_of_date=None, symbols=["000001.SZ"],
    )
    calls = []
    b = selection_service.run_selection(
        cache=populated_cache, config=config, as_of_date=None, symbols=["000001.SZ"],
        on_progress=lambda *args: calls.append(args),
    )
    assert a.candidates == b.candidates
    # cached path should still emit "done" but skip intermediate stages
    stages = [c[0] for c in calls]
    assert stages == ["done"]
```

- [ ] **Step 2: Run, confirm fail**

Expected: FAIL — current implementation always emits 5 stages.

- [ ] **Step 3: Add cache to selection_service**

Top of file:

```python
import hashlib
import json
from dataclasses import asdict

_RESULT_CACHE: dict[str, "SelectionResult"] = {}


def _cache_key(*, config: FactorSelectorConfig, as_of_date, symbols) -> str:
    payload = {
        "config": _config_to_dict(config),
        "as_of_date": str(as_of_date) if as_of_date is not None else None,
        "symbols": sorted(symbols) if symbols else None,
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()
```

In `run_selection`, before the `progress("load_panel", ...)` line:

```python
key = _cache_key(config=config, as_of_date=as_of_date, symbols=symbols)
cached = _RESULT_CACHE.get(key)
if cached is not None:
    progress = on_progress or _noop
    progress("done", 1.0, "命中缓存")
    return cached
```

After the result is built, before returning:

```python
_RESULT_CACHE[key] = result
return result
```

(Adapt the existing return so the result is assigned to a local variable first.)

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_services_selection.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/quant_backtest/services/selection_service.py tests/test_services_selection.py
git commit -m "feat(services): cache selection results by config+date+universe hash"
```

### Task 6.2: README + devlog + ADR

**Files:**
- Modify: `README.md`
- Create: `docs/devlog/2026-05-10-fastapi-readonly-backend.md`
- Create: `docs/adr/0009-fastapi-readonly-backend.md`

- [ ] **Step 1: Add "Run the API" section to README.md**

After the existing CLI examples, add:

```markdown
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

Endpoints (browse interactive docs at http://127.0.0.1:8000/docs):

- `GET  /api/health`, `/api/version`
- `GET  /api/symbols` — list/search cached symbols
- `GET  /api/symbols/{symbol}`, `/api/bars/{symbol}` — single-symbol info and K-line
- `GET  /api/cache/coverage` — full-market cache coverage
- `GET  /api/selection/factors`, `/api/selection/defaults` — factor metadata
- `POST /api/selection/jobs` — start a selection (returns job_id)
- `GET  /api/selection/jobs/{id}`, `/api/selection/jobs/{id}/stream` — poll or SSE-stream progress
- `GET  /api/reports`, `/api/reports/{id}`, `/api/reports/{id}/equity|trades|sweep` — read-only backtest reports

Reports are produced by `quant-backtest sweep` and `quant-backtest validate`; pass `--no-report` to skip on-disk output.
```

- [ ] **Step 2: Write devlog**

Create `docs/devlog/2026-05-10-fastapi-readonly-backend.md`:

```markdown
# FastAPI Read-Only Backend

**Date:** 2026-05-10
**Spec:** [docs/superpowers/specs/2026-05-10-fastapi-readonly-backend-design.md]
**ADR:** [docs/adr/0009-fastapi-readonly-backend.md]

## Summary

Added a read-only HTTP layer over the existing quant_backtest modules, plus a stable
backtest report artifact format. Three resource groups: data (symbols / bars / coverage),
selection (job-based with SSE progress), reports (sweep + validate, written by CLI).

## Why

CLI-only is the wrong UI for browsing. The web frontend planned next needs a structured
JSON surface; building it on top of CLI subprocess calls would couple HTTP to text formatting.

## Key decisions

- Three-layer split: services/ (shared business), api/ (HTTP only), CLI also goes
  through services/. Logic exists in one place.
- No queue, no DB, no auth. In-process JobRegistry, single-process server.
- Backtests stay CLI-only. The API only reads finished reports.
- SSE for selection progress; selection synchronous-with-progress is the only "active"
  endpoint.

## Verification

- `uv run pytest` — full suite green including new services / api / reports tests
- Manual SSE smoke via `curl -N` against /api/selection/jobs/{id}/stream
```

- [ ] **Step 3: Write ADR**

Create `docs/adr/0009-fastapi-readonly-backend.md`:

```markdown
# ADR 0009: FastAPI Read-Only Backend

## Status
Accepted

## Context
Muce was CLI-only. A web frontend is planned. We need an HTTP layer that exposes
data, selection, and backtest reports without coupling to CLI text output and without
introducing infrastructure (Redis / Celery / DB) that's overkill for a single-user
local tool.

## Decision

1. Add a `services/` layer that wraps existing modules; CLI and API both call it.
2. Define a stable on-disk format under `reports/sweeps/` and `reports/validations/`
   with manifest.json, parquet artifacts, and config.json. CLI writes; API reads.
3. Use FastAPI + uvicorn + sse-starlette. JobRegistry is an in-process dict with TTL.
4. Selection is the only endpoint that triggers work; backtests stay CLI-only.

## Consequences

Positive:
- Single source of truth for business logic.
- Reports become reproducible and inspectable independent of the engine that produced them.
- Adding a frontend later is now a UI problem, not an integration problem.

Negative / accepted:
- Job state lost on restart.
- No multi-user / multi-process scaling. Acceptable for v1.
- Selection >30s falls back to CLI; we surface this clearly to users.
```

- [ ] **Step 4: Update docs/README.md index**

Add lines under "Current Docs":

```
- [FastAPI Read-Only Backend](devlog/2026-05-10-fastapi-readonly-backend.md)
- [ADR 0009: FastAPI Read-Only Backend](adr/0009-fastapi-readonly-backend.md)
```

- [ ] **Step 5: Commit**

```bash
git add README.md docs/devlog/2026-05-10-fastapi-readonly-backend.md \
        docs/adr/0009-fastapi-readonly-backend.md docs/README.md
git commit -m "docs: API quickstart, devlog, ADR 0009"
```

### Task 6.3: Final regression sweep

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: ALL passing.

- [ ] **Step 2: Lint check (if project uses any)**

Run: `uv run python -m compileall src/quant_backtest`
Expected: no errors.

- [ ] **Step 3: Verify CLI scripts still work end-to-end**

Run: `uv run quant-data --help`
Run: `uv run quant-backtest --help`
Run: `uv run quant-select --help`
Run: `uv run quant-api --help` (uvicorn delegates; even if `--help` is uvicorn's, the script must resolve)
Expected: each prints help without import errors.

- [ ] **Step 4: Open `/docs` and visually confirm OpenAPI**

Run: `uv run quant-api &` ; open `http://127.0.0.1:8000/docs` ; confirm three groups (data, selection, reports) plus system endpoints. Stop server.

- [ ] **Step 5: No commit needed unless cleanup happened**

If the regression sweep surfaced an issue, fix and commit per task style; otherwise this task is verification-only.

---

## Self-Review Notes

**Spec coverage:** Each spec section maps to phases:
- §1 background / §2 architecture → Plan header + Task 1.1 / 3.2 (skeleton choices)
- §3 module layout → Tasks 1.1, 2.1, 3.2, 5.1 (each module created)
- §4.1 data routes → Task 3.3
- §4.2 selection routes (jobs + SSE) → Tasks 5.2, 5.3
- §4.3 reports routes → Task 4.2
- §4.4 system routes → Task 3.2
- §5 reports schema → Tasks 2.1, 2.2, 2.3
- §6 CLI changes → Tasks 1.7, 2.4, 2.5
- §7 testing strategy → Tests added in every functional task
- §8 implementation order → Phases 1-6 mirror the six steps
- §9 risks (caching, timeout) → Tasks 5.2 (timeout), 6.1 (cache)

**Type consistency check:** `JobState`, `JobRegistry`, `SelectionResult`, `ReportManifest` / `SweepManifest` / `ValidateManifest`, `BarsResult`, `CoverageEntry`, `SymbolRow`, `SymbolInfo` — all introduced in their first task and reused with the same field names through the plan.

**Placeholder scan:** No "TBD" / "implement later" / unresolved references. Implementation steps include code; tests include assertions; commands include expected output.
