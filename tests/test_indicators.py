from __future__ import annotations

import pandas as pd
import pytest

from quant_backtest.features import (
    TechnicalIndicatorConfig,
    add_technical_indicators,
    bollinger_bands,
    kdj,
    macd,
    obv,
    rsi,
    sma,
    volume_ma,
)
from tests.conftest import make_bars


def test_basic_moving_average_and_volume_ma() -> None:
    close = pd.Series([1.0, 2.0, 3.0, 4.0])
    volume = pd.Series([10.0, 20.0, 30.0, 40.0])

    assert sma(close, 2).tolist() == [pytest.approx(float("nan"), nan_ok=True), 1.5, 2.5, 3.5]
    result = volume_ma(volume, windows=(2,))
    assert result["vol_ma_2"].tolist() == [pytest.approx(float("nan"), nan_ok=True), 15.0, 25.0, 35.0]


def test_macd_rsi_bollinger_obv_outputs_expected_columns() -> None:
    close = pd.Series([float(value) for value in range(1, 41)])
    volume = pd.Series([100.0] * 40)

    macd_frame = macd(close)
    assert list(macd_frame.columns) == ["macd_diff", "macd_dea", "macd_hist"]
    assert macd_frame["macd_diff"].iloc[-1] > 0

    rsi_value = rsi(close, window=14)
    assert rsi_value.iloc[-1] == pytest.approx(100.0)

    bands = bollinger_bands(close, window=20)
    assert list(bands.columns) == ["boll_mid", "boll_upper", "boll_lower"]
    assert bands["boll_upper"].iloc[-1] > bands["boll_mid"].iloc[-1] > bands["boll_lower"].iloc[-1]

    assert obv(close, volume).iloc[-1] == 3900.0


def test_kdj_uses_a_share_style_initial_50_recursive_smoothing() -> None:
    high = pd.Series([10.0, 10.0, 10.0])
    low = pd.Series([0.0, 0.0, 0.0])
    close = pd.Series([5.0, 5.0, 10.0])

    result = kdj(high, low, close, window=3, k_period=3, d_period=3)

    assert pd.isna(result["kdj_k"].iloc[0])
    assert pd.isna(result["kdj_k"].iloc[1])
    assert result["kdj_k"].iloc[2] == pytest.approx(66.6666666667)
    assert result["kdj_d"].iloc[2] == pytest.approx(55.5555555556)
    assert result["kdj_j"].iloc[2] == pytest.approx(88.8888888889)


def test_add_technical_indicators_keeps_symbols_separate() -> None:
    first = make_bars("000001.SZ", rows=6)
    second = make_bars("600000.SH", rows=6)
    second["close"] = [100.0] * 6
    frame = pd.concat([first, second], ignore_index=True)

    result = add_technical_indicators(
        frame,
        config=TechnicalIndicatorConfig(
            ma_windows=(3,),
            ema_windows=(),
            volume_ma_windows=(3,),
            rsi_window=3,
            kdj_window=3,
            macd_fast=2,
            macd_slow=3,
            macd_signal=2,
            boll_window=3,
            atr_window=3,
        ),
    )

    first_symbol = result[result["symbol"].eq("000001.SZ")]
    second_symbol = result[result["symbol"].eq("600000.SH")]
    assert first_symbol["ma_3"].iloc[2] == pytest.approx(11.0)
    assert second_symbol["ma_3"].iloc[2] == pytest.approx(100.0)
    assert "macd_hist" in result.columns
    assert "kdj_j" in result.columns
    assert "atr_3" in result.columns


def test_add_technical_indicators_can_return_only_features() -> None:
    frame = make_bars("000001.SZ", rows=5)
    result = add_technical_indicators(
        frame,
        config=TechnicalIndicatorConfig(
            ma_windows=(2,),
            ema_windows=(),
            volume_ma_windows=(),
            rsi_window=2,
            kdj_window=2,
            macd_fast=2,
            macd_slow=3,
            macd_signal=2,
            boll_window=2,
            atr_window=2,
        ),
        include_original=False,
    )

    assert "close" not in result.columns
    assert "ma_2" in result.columns


def test_add_technical_indicators_requires_ohlcv() -> None:
    with pytest.raises(KeyError, match="missing required OHLCV columns"):
        add_technical_indicators(pd.DataFrame({"close": [1.0]}))
