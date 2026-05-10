from __future__ import annotations

import pytest

from quant_backtest.data.cache import ParquetCache
from quant_backtest.selection import FactorSelectorConfig
from quant_backtest.services import selection_service
from tests.conftest import make_bars


@pytest.fixture()
def populated_cache(tmp_path) -> ParquetCache:
    cache = ParquetCache(tmp_path)
    # 80 business days of monotonically rising close — keeps validate_daily_bars happy
    # (no gaps, no zero volume, no large jumps with the small 1-unit step).
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=80, start="2024-01-02"))
    return cache


def test_run_selection_returns_candidates(populated_cache):
    config = FactorSelectorConfig(min_score=0, top_n=5)
    result = selection_service.run_selection(
        cache=populated_cache,
        config=config,
        as_of_date=None,
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


def test_run_selection_emits_progress(populated_cache):
    selection_service.clear_cache()
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


def test_run_selection_caches_repeated_calls(populated_cache):
    selection_service.clear_cache()
    config = FactorSelectorConfig(min_score=0, top_n=5)
    a = selection_service.run_selection(
        cache=populated_cache, config=config, as_of_date=None, symbols=["000001.SZ"],
    )
    calls: list[tuple[str, float, str]] = []
    b = selection_service.run_selection(
        cache=populated_cache,
        config=config,
        as_of_date=None,
        symbols=["000001.SZ"],
        on_progress=lambda stage, progress, msg: calls.append((stage, progress, msg)),
    )
    assert a.candidates == b.candidates
    stages = [stage for stage, _, _ in calls]
    assert stages == ["done"]
