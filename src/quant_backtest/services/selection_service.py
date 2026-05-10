"""Service-layer wrapper for daily multi-factor stock selection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
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
from quant_backtest.selection.factors import FACTOR_COLUMNS

ProgressCallback = Callable[[str, float, str], None]

_RESULT_CACHE: dict[str, "SelectionResult"] = {}


def _cache_key(
    *,
    config: FactorSelectorConfig,
    as_of_date: date | str | None,
    symbols: list[str] | None,
    source: str,
    adjust: str,
) -> str:
    payload = {
        "config": _config_to_dict(config),
        "as_of_date": str(as_of_date) if as_of_date is not None else None,
        "symbols": sorted(symbols) if symbols else None,
        "source": source,
        "adjust": adjust,
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def clear_cache() -> None:
    """Reset the in-process result cache (intended for tests)."""

    _RESULT_CACHE.clear()


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

    key = _cache_key(
        config=config,
        as_of_date=as_of_date,
        symbols=symbols,
        source=source,
        adjust=adjust,
    )
    cached = _RESULT_CACHE.get(key)
    if cached is not None:
        progress("done", 1.0, "命中缓存")
        return cached

    progress("load_panel", 0.10, "加载缓存面板...")
    universe = list(symbols) if symbols else cache.available_symbols(source=source, adjust=adjust)
    panel = cache.read_many(source=source, adjust=adjust, symbols=universe)

    progress("compute_indicators", 0.40, "计算技术指标...")
    factor_table = build_factor_table(panel, config=config)

    progress("score", 0.70, "因子打分...")
    if as_of_date is None:
        as_of_ts = factor_table["date"].max()
    else:
        as_of_ts = pd.Timestamp(as_of_date)

    progress("filter_rank", 0.90, "过滤 + Top-N 排序...")
    candidates_frame = select_candidates(
        factor_table,
        date=as_of_ts,
        top_n=config.top_n,
    )

    candidates = []
    for record in candidates_frame.to_dict(orient="records"):
        candidates.append(
            {
                "symbol": record.get("symbol"),
                "score": int(record.get("factor_score", 0)),
                "factors_hit": [
                    name for name in FACTOR_COLUMNS if bool(record.get(name))
                ],
                "reasons": record.get("factor_reasons", ""),
            }
        )

    snapshot = factor_table[factor_table["date"].eq(as_of_ts)]
    passed_min_score = int(snapshot["selected"].sum()) if not snapshot.empty else 0

    summary = {
        "total_universe": len(universe),
        "passed_min_score": passed_min_score,
        "top_n_returned": int(min(passed_min_score, config.top_n)),
    }
    progress("done", 1.0, "完成")

    result = SelectionResult(
        as_of_date=str(pd.Timestamp(as_of_ts).date()),
        config=_config_to_dict(config),
        candidates=candidates,
        summary=summary,
    )
    _RESULT_CACHE[key] = result
    return result


def _config_to_dict(config: FactorSelectorConfig) -> dict:
    payload = asdict(config)
    payload["require_factors"] = list(config.require_factors)
    payload["exclude_factors"] = list(config.exclude_factors)
    return payload
