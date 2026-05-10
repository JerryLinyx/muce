from __future__ import annotations

import pandas as pd


def talib_available() -> bool:
    try:
        import talib  # noqa: F401
    except ImportError:
        return False
    return True


def talib_reference_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Return selected TA-Lib reference indicators for comparison tests.

    This module is intentionally optional. It should not be imported by runtime
    strategy code unless the `indicators` extra is installed.
    """

    try:
        import talib
    except ImportError as exc:
        raise RuntimeError("install quant-backtest[indicators] to use TA-Lib oracle") from exc

    required = ["high", "low", "close", "volume"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise KeyError(f"missing required columns for TA-Lib comparison: {missing}")

    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)

    macd, macd_signal, macd_hist = talib.MACD(
        close,
        fastperiod=12,
        slowperiod=26,
        signalperiod=9,
    )
    slow_k, slow_d = talib.STOCH(
        high,
        low,
        close,
        fastk_period=9,
        slowk_period=3,
        slowk_matype=0,
        slowd_period=3,
        slowd_matype=0,
    )
    return pd.DataFrame(
        {
            "talib_sma_20": talib.SMA(close, timeperiod=20),
            "talib_ema_12": talib.EMA(close, timeperiod=12),
            "talib_macd_diff": macd,
            "talib_macd_dea": macd_signal,
            "talib_macd_hist": macd_hist,
            "talib_rsi_14": talib.RSI(close, timeperiod=14),
            "talib_kdj_k": slow_k,
            "talib_kdj_d": slow_d,
            "talib_atr_14": talib.ATR(high, low, close, timeperiod=14),
        },
        index=frame.index,
    )
