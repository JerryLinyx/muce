from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import pandas as pd

from quant_backtest.data.constants import OHLC_COLUMNS, STANDARD_DAILY_COLUMNS


@dataclass(frozen=True)
class QualityReport:
    hard_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.hard_errors


class DataQualityError(ValueError):
    def __init__(self, report: QualityReport):
        self.report = report
        super().__init__("; ".join(report.hard_errors))


def normalize_daily_bars(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in STANDARD_DAILY_COLUMNS if column not in df.columns]
    if missing:
        raise DataQualityError(QualityReport([f"missing columns: {', '.join(missing)}"]))

    out = df.loc[:, STANDARD_DAILY_COLUMNS].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.normalize()
    for column in ["symbol", "adjust", "source", "market", "frequency", "calendar", "currency"]:
        out[column] = out[column].astype("string")
    out["query_time"] = out["query_time"].astype("string")

    for column in ["open", "high", "low", "close", "pre_close", "volume", "amount"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    for column in ["trade_status", "is_st"]:
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0).astype("int64")

    return out.sort_values(["symbol", "date"]).reset_index(drop=True)


def validate_daily_bars(
    df: pd.DataFrame,
    *,
    expected_metadata: Mapping[str, str] | None = None,
    raise_on_error: bool = True,
) -> QualityReport:
    hard_errors: list[str] = []
    warnings: list[str] = []

    missing = [column for column in STANDARD_DAILY_COLUMNS if column not in df.columns]
    if missing:
        hard_errors.append(f"missing columns: {', '.join(missing)}")
        report = QualityReport(hard_errors, warnings)
        if raise_on_error:
            raise DataQualityError(report)
        return report

    work = normalize_daily_bars(df)

    if work["date"].isna().any():
        hard_errors.append("date contains empty or invalid values")
    if work["symbol"].isna().any() or (work["symbol"].str.len() == 0).any():
        hard_errors.append("symbol contains empty values")
    if work.duplicated(["date", "symbol"]).any():
        hard_errors.append("duplicate date + symbol rows")

    normal_trade = work["trade_status"].eq(1)
    if work.loc[normal_trade, OHLC_COLUMNS].isna().any().any():
        hard_errors.append("normal trading rows contain missing OHLC")
    if (work.loc[normal_trade, OHLC_COLUMNS] <= 0).any().any():
        hard_errors.append("normal trading rows contain non-positive OHLC")

    for symbol, group in work.groupby("symbol", sort=False):
        if not group["date"].is_monotonic_increasing:
            hard_errors.append(f"{symbol} dates are not sorted")

    if expected_metadata:
        for key, expected in expected_metadata.items():
            if key not in work.columns:
                hard_errors.append(f"metadata column {key!r} is missing")
                continue
            values = set(work[key].dropna().astype(str))
            if values != {str(expected)}:
                hard_errors.append(
                    f"metadata mismatch for {key}: expected {expected!r}, got {sorted(values)!r}"
                )

    _warn_if(work["volume"].eq(0).any(), warnings, "volume contains zero values")
    _warn_if(work["amount"].eq(0).any(), warnings, "amount contains zero values")
    _warn_if(work["trade_status"].eq(0).any(), warnings, "trade_status contains suspended rows")
    _warn_if(work["is_st"].eq(1).any(), warnings, "is_st contains ST rows")
    _warn_if(work["pre_close"].isna().any(), warnings, "pre_close contains missing values")
    _warn_if(_has_trading_day_gaps(work), warnings, "date gaps detected within one or more symbols")
    _warn_if(_has_large_price_jumps(work), warnings, "large close-to-close price jumps detected")

    report = QualityReport(hard_errors, warnings)
    if hard_errors and raise_on_error:
        raise DataQualityError(report)
    return report


def _warn_if(condition: bool, warnings: list[str], message: str) -> None:
    if condition:
        warnings.append(message)


def _has_trading_day_gaps(df: pd.DataFrame) -> bool:
    for _, group in df.groupby("symbol", sort=False):
        gaps = group["date"].diff().dt.days.dropna()
        if gaps.gt(10).any():
            return True
    return False


def _has_large_price_jumps(df: pd.DataFrame) -> bool:
    for _, group in df.groupby("symbol", sort=False):
        pct = group["close"].pct_change().abs()
        if pct.gt(0.35).any():
            return True
    return False
