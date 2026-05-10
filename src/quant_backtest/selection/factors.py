from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_backtest.features import TechnicalIndicatorConfig, add_technical_indicators


@dataclass(frozen=True)
class FactorSelectorConfig:
    ma_short: int = 20
    ma_long: int = 60
    kdj_window: int = 9
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    rsi_window: int = 14
    rsi_threshold: float = 55.0
    volume_window: int = 20
    volume_multiplier: float = 1.5
    boll_window: int = 20
    boll_std: float = 2.0
    min_score: int = 2
    top_n: int = 20
    exclude_suspended: bool = True
    exclude_st: bool = True
    require_factors: tuple[str, ...] = ()
    exclude_factors: tuple[str, ...] = ()


FACTOR_COLUMNS = [
    "ma_breakout",
    "kdj_golden_cross",
    "macd_golden_cross",
    "rsi_momentum",
    "volume_breakout",
    "boll_breakout",
]


def build_factor_table(frame: pd.DataFrame, config: FactorSelectorConfig | None = None) -> pd.DataFrame:
    config = config or FactorSelectorConfig()
    _validate_input(frame)
    _validate_factor_names(config.require_factors)
    _validate_factor_names(config.exclude_factors)
    indicator_config = TechnicalIndicatorConfig(
        ma_windows=tuple(sorted({config.ma_short, config.ma_long})),
        ema_windows=(config.macd_fast, config.macd_slow),
        volume_ma_windows=(config.volume_window,),
        rsi_window=config.rsi_window,
        kdj_window=config.kdj_window,
        macd_fast=config.macd_fast,
        macd_slow=config.macd_slow,
        macd_signal=config.macd_signal,
        boll_window=config.boll_window,
        boll_std=config.boll_std,
    )
    data = add_technical_indicators(frame, config=indicator_config).sort_values(["symbol", "date"]).copy()
    grouped = data.groupby("symbol", sort=False, group_keys=False)

    ma_short = data[f"ma_{config.ma_short}"]
    ma_long = data[f"ma_{config.ma_long}"]
    previous_close = grouped["close"].shift(1)
    previous_ma_short = grouped[f"ma_{config.ma_short}"].shift(1)
    previous_k = grouped["kdj_k"].shift(1)
    previous_d = grouped["kdj_d"].shift(1)
    previous_macd = grouped["macd_diff"].shift(1)
    previous_dea = grouped["macd_dea"].shift(1)
    previous_boll_upper = grouped["boll_upper"].shift(1)

    data["ma_breakout"] = (data["close"] > ma_short) & (previous_close <= previous_ma_short) & (ma_short > ma_long)
    data["kdj_golden_cross"] = (data["kdj_k"] > data["kdj_d"]) & (previous_k <= previous_d)
    data["macd_golden_cross"] = (data["macd_diff"] > data["macd_dea"]) & (previous_macd <= previous_dea)
    data["rsi_momentum"] = data[f"rsi_{config.rsi_window}"] >= config.rsi_threshold
    data["volume_breakout"] = data["volume"] >= data[f"vol_ma_{config.volume_window}"] * config.volume_multiplier
    data["boll_breakout"] = (data["close"] > data["boll_upper"]) & (previous_close <= previous_boll_upper)

    if config.exclude_suspended and "trade_status" in data.columns:
        tradable = data["trade_status"].eq(1)
    else:
        tradable = pd.Series(True, index=data.index)
    if config.exclude_st and "is_st" in data.columns:
        tradable = tradable & data["is_st"].eq(0)
    data["tradable"] = tradable

    data[FACTOR_COLUMNS] = data[FACTOR_COLUMNS].fillna(False).astype(bool)
    data["factor_score"] = data[FACTOR_COLUMNS].sum(axis=1).astype(int)
    data["factor_reasons"] = data.apply(_factor_reasons, axis=1)
    required = pd.Series(True, index=data.index)
    for factor in config.require_factors:
        required = required & data[factor]
    excluded = pd.Series(False, index=data.index)
    for factor in config.exclude_factors:
        excluded = excluded | data[factor]
    data["selected"] = data["tradable"] & data["factor_score"].ge(config.min_score) & required & ~excluded
    return data


def select_candidates(
    factor_table: pd.DataFrame,
    *,
    date: str | pd.Timestamp | None = None,
    top_n: int | None = None,
    latest: bool = False,
) -> pd.DataFrame:
    data = factor_table.copy()
    if date is not None:
        data = data[data["date"].eq(pd.to_datetime(date))]
    elif latest and not data.empty:
        data = data[data["date"].eq(data["date"].max())]

    selected = data[data["selected"]].copy()
    if selected.empty:
        return selected
    selected = selected.sort_values(
        ["date", "factor_score", "amount", "volume", "symbol"],
        ascending=[True, False, False, False, True],
    )
    limit = top_n if top_n is not None else len(selected)
    return selected.groupby("date", sort=False, group_keys=False).head(limit).reset_index(drop=True)


def _factor_reasons(row: pd.Series) -> str:
    return ",".join(column for column in FACTOR_COLUMNS if bool(row[column]))


def _validate_input(frame: pd.DataFrame) -> None:
    required = ["date", "symbol", "open", "high", "low", "close", "volume", "amount"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise KeyError(f"missing required selector columns: {missing}")


def _validate_factor_names(factors: tuple[str, ...]) -> None:
    unknown = sorted(set(factors).difference(FACTOR_COLUMNS))
    if unknown:
        raise ValueError(f"unknown selector factors: {unknown}; valid factors: {FACTOR_COLUMNS}")
