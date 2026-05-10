from __future__ import annotations

import math
from typing import Any

import pandas as pd


def compute_equity_metrics(
    values: pd.Series,
    *,
    start_cash: float,
    periods_per_year: int = 252,
) -> dict[str, float | None]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return {
            "start_cash": float(start_cash),
            "final_value": None,
            "total_return": None,
            "annual_return": None,
            "max_drawdown": None,
            "sharpe": None,
        }

    final_value = float(clean.iloc[-1])
    total_return = final_value / start_cash - 1 if start_cash else None
    annual_return = None
    if total_return is not None and len(clean) > 1:
        annual_return = (1 + total_return) ** (periods_per_year / (len(clean) - 1)) - 1

    running_max = clean.cummax()
    drawdown = clean / running_max - 1
    max_drawdown = abs(float(drawdown.min()))

    returns = clean.pct_change().dropna()
    sharpe = None
    if len(returns) > 1:
        std = float(returns.std(ddof=1))
        if std > 0:
            sharpe = float(returns.mean() / std * math.sqrt(periods_per_year))

    return {
        "start_cash": float(start_cash),
        "final_value": final_value,
        "total_return": float(total_return) if total_return is not None else None,
        "annual_return": float(annual_return) if annual_return is not None else None,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
    }


def value_frame_from_vectorbt(portfolio: Any) -> pd.DataFrame:
    values = portfolio.value()
    if isinstance(values, pd.Series):
        return values.to_frame()
    return values
