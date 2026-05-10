from __future__ import annotations

import pandas as pd
import pytest

from quant_backtest.features import (
    TechnicalIndicatorConfig,
    add_technical_indicators,
    talib_available,
    talib_reference_indicators,
)


pytestmark = pytest.mark.skipif(not talib_available(), reason="TA-Lib optional extra is not installed")


def test_talib_reference_matches_core_overlap_for_basic_indicators() -> None:
    frame = _reference_frame()
    ours = add_technical_indicators(frame, config=TechnicalIndicatorConfig())
    theirs = talib_reference_indicators(frame)

    _assert_close(ours["ma_20"], theirs["talib_sma_20"], tolerance=1e-10)
    _assert_close(ours["ema_12"], theirs["talib_ema_12"], tolerance=1e-10)


def test_talib_reference_exposes_expected_formula_differences() -> None:
    frame = _reference_frame()
    ours = add_technical_indicators(frame, config=TechnicalIndicatorConfig())
    theirs = talib_reference_indicators(frame)

    assert _max_abs_diff(ours["rsi_14"], theirs["talib_rsi_14"]) >= 0
    assert _max_abs_diff(ours["atr_14"], theirs["talib_atr_14"]) >= 0


def _reference_frame() -> pd.DataFrame:
    index = pd.RangeIndex(80)
    close = pd.Series([20 + idx * 0.2 + (idx % 7) * 0.15 for idx in index])
    frame = pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": [1000 + idx * 5 for idx in index],
        }
    )
    return frame


def _assert_close(left: pd.Series, right: pd.Series, *, tolerance: float) -> None:
    assert _max_abs_diff(left, right) <= tolerance


def _max_abs_diff(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
    if aligned.empty:
        return 0.0
    return float((aligned["left"] - aligned["right"]).abs().max())
