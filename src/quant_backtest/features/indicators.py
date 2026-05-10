from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

import pandas as pd


@dataclass(frozen=True)
class TechnicalIndicatorConfig:
    ma_windows: tuple[int, ...] = (5, 10, 20, 60)
    ema_windows: tuple[int, ...] = (12, 26)
    volume_ma_windows: tuple[int, ...] = (5, 20)
    rsi_window: int = 14
    kdj_window: int = 9
    kdj_k_period: int = 3
    kdj_d_period: int = 3
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    boll_window: int = 20
    boll_std: float = 2.0
    atr_window: int = 14


REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def add_technical_indicators(
    frame: pd.DataFrame,
    *,
    config: TechnicalIndicatorConfig | None = None,
    include_original: bool = True,
) -> pd.DataFrame:
    """Add standard daily technical indicators to OHLCV rows.

    If a ``symbol`` column is present, indicators are computed independently per
    symbol after sorting by ``date`` when available.
    """

    config = config or TechnicalIndicatorConfig()
    _validate_columns(frame, REQUIRED_COLUMNS)

    if frame.empty:
        return frame.copy() if include_original else pd.DataFrame(index=frame.index)

    sort_columns = [column for column in ("symbol", "date") if column in frame.columns]
    ordered = frame.sort_values(sort_columns).copy() if sort_columns else frame.copy()

    if "symbol" in ordered.columns:
        pieces = [
            _add_group_indicators(group, config=config, include_original=include_original)
            for _, group in ordered.groupby("symbol", sort=False, group_keys=False)
        ]
        result = pd.concat(pieces).sort_index()
    else:
        result = _add_group_indicators(ordered, config=config, include_original=include_original)

    return result.reindex(frame.index)


def sma(close: pd.Series, window: int) -> pd.Series:
    _validate_window(window, "window")
    return close.rolling(window=window, min_periods=window).mean()


def ema(close: pd.Series, span: int) -> pd.Series:
    _validate_window(span, "span")
    return close.ewm(span=span, adjust=False, min_periods=span).mean()


def macd(
    close: pd.Series,
    *,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    _validate_window(fast, "fast")
    _validate_window(slow, "slow")
    _validate_window(signal, "signal")
    if fast >= slow:
        raise ValueError("fast must be smaller than slow")

    diff = ema(close, fast) - ema(close, slow)
    dea = diff.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = diff - dea
    return pd.DataFrame({"macd_diff": diff, "macd_dea": dea, "macd_hist": hist})


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    _validate_window(window, "window")
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    value = 100 - 100 / (1 + rs)
    value = value.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    value = value.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    return value


def kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    *,
    window: int = 9,
    k_period: int = 3,
    d_period: int = 3,
) -> pd.DataFrame:
    _validate_window(window, "window")
    _validate_window(k_period, "k_period")
    _validate_window(d_period, "d_period")
    lowest_low = low.rolling(window=window, min_periods=window).min()
    highest_high = high.rolling(window=window, min_periods=window).max()
    spread = highest_high - lowest_low
    rsv = ((close - lowest_low) / spread * 100).where(spread != 0, 50.0)
    k = _sma_like_recursive(rsv, period=k_period, initial=50.0)
    d = _sma_like_recursive(k, period=d_period, initial=50.0)
    j = 3 * k - 2 * d
    return pd.DataFrame({"kdj_k": k, "kdj_d": d, "kdj_j": j})


def bollinger_bands(
    close: pd.Series,
    *,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    _validate_window(window, "window")
    middle = sma(close, window)
    std = close.rolling(window=window, min_periods=window).std(ddof=0)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return pd.DataFrame({"boll_mid": middle, "boll_upper": upper, "boll_lower": lower})


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    *,
    window: int = 14,
) -> pd.Series:
    _validate_window(window, "window")
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def volume_ma(volume: pd.Series, windows: Iterable[int] = (5, 20)) -> pd.DataFrame:
    data = {}
    for window in windows:
        _validate_window(window, "window")
        data[f"vol_ma_{window}"] = volume.rolling(window=window, min_periods=window).mean()
    return pd.DataFrame(data, index=volume.index)


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda value: 1 if value > 0 else -1 if value < 0 else 0)
    direction.iloc[0] = 0
    return (direction * volume).cumsum()


def _add_group_indicators(
    group: pd.DataFrame,
    *,
    config: TechnicalIndicatorConfig,
    include_original: bool,
) -> pd.DataFrame:
    output = group.copy() if include_original else pd.DataFrame(index=group.index)

    for window in config.ma_windows:
        output[f"ma_{window}"] = sma(group["close"], window)
    for window in config.ema_windows:
        output[f"ema_{window}"] = ema(group["close"], window)

    output[f"rsi_{config.rsi_window}"] = rsi(group["close"], config.rsi_window)
    output = output.join(
        macd(
            group["close"],
            fast=config.macd_fast,
            slow=config.macd_slow,
            signal=config.macd_signal,
        )
    )
    output = output.join(
        kdj(
            group["high"],
            group["low"],
            group["close"],
            window=config.kdj_window,
            k_period=config.kdj_k_period,
            d_period=config.kdj_d_period,
        )
    )
    output = output.join(
        bollinger_bands(group["close"], window=config.boll_window, num_std=config.boll_std)
    )
    output[f"atr_{config.atr_window}"] = atr(
        group["high"],
        group["low"],
        group["close"],
        window=config.atr_window,
    )
    output = output.join(volume_ma(group["volume"], config.volume_ma_windows))
    output["obv"] = obv(group["close"], group["volume"])
    return output


def _sma_like_recursive(series: pd.Series, *, period: int, initial: float) -> pd.Series:
    previous = initial
    values: list[float | None] = []
    for value in series:
        if pd.isna(value):
            values.append(None)
            continue
        previous = (previous * (period - 1) + float(value)) / period
        values.append(previous)
    return pd.Series(values, index=series.index, dtype="float64")


def _validate_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"missing required OHLCV columns: {missing}")


def _validate_window(window: int, name: str) -> None:
    if int(window) < 1:
        raise ValueError(f"{name} must be >= 1")
