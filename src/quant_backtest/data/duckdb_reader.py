from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from quant_backtest.data.constants import SOURCE_BAOSTOCK, Adjust


class DuckDBReader:
    """SQL query layer over the Parquet cache.

    Parquet remains the source of truth. DuckDB is used only to query partitioned
    files without loading the full universe into pandas first.
    """

    def __init__(self, root: str | Path = "data/cache/a_share/daily") -> None:
        self.root = Path(root)

    def daily_bars(
        self,
        *,
        source: str = SOURCE_BAOSTOCK,
        adjust: Adjust = "qfq",
        symbols: list[str] | None = None,
        start: str | None = None,
        end: str | None = None,
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        con = _connect()
        try:
            selected_columns = ", ".join(columns) if columns else "*"
            query = f"select {selected_columns} from read_parquet(?, hive_partitioning=true) where true"
            params: list[Any] = [self._glob(source=source, adjust=adjust)]
            if symbols:
                query += " and symbol in (" + ",".join(["?"] * len(symbols)) + ")"
                params.extend(symbols)
            if start:
                query += " and date >= ?"
                params.append(pd.to_datetime(start).date())
            if end:
                query += " and date <= ?"
                params.append(pd.to_datetime(end).date())
            query += " order by symbol, date"
            return con.execute(query, params).fetchdf()
        finally:
            con.close()

    def inspect(self, *, source: str = SOURCE_BAOSTOCK, adjust: Adjust = "qfq") -> dict[str, Any]:
        con = _connect()
        try:
            query = """
                select
                    count(*) as row_count,
                    count(distinct symbol) as symbol_count,
                    min(date) as date_start,
                    max(date) as date_end,
                    sum(case when open is null or high is null or low is null or close is null then 1 else 0 end) as missing_ohlc_count,
                    sum(case when trade_status = 0 then 1 else 0 end) as suspended_rows,
                    sum(case when is_st = 1 then 1 else 0 end) as st_rows
                from read_parquet(?, hive_partitioning=true)
            """
            row = con.execute(query, [self._glob(source=source, adjust=adjust)]).fetchone()
        finally:
            con.close()
        return {
            "source": source,
            "adjust": adjust,
            "row_count": int(row[0] or 0),
            "symbol_count": int(row[1] or 0),
            "date_range": [str(row[2]) if row[2] else None, str(row[3]) if row[3] else None],
            "missing_ohlc_count": int(row[4] or 0),
            "suspended_rows": int(row[5] or 0),
            "st_rows": int(row[6] or 0),
        }

    def _glob(self, *, source: str, adjust: str) -> str:
        return str(self.root / f"source={source}" / f"adjust={adjust}" / "symbol=*" / "part.parquet")


def duckdb_available() -> bool:
    try:
        import duckdb  # noqa: F401
    except ImportError:
        return False
    return True


def _connect():
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("install quant-backtest[query] to use DuckDBReader") from exc
    return duckdb.connect(database=":memory:")
