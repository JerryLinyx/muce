from __future__ import annotations

import re

SUPPORTED_SOURCES = {"baostock", "akshare", "tushare"}
INTERNAL_SYMBOL_RE = re.compile(r"^\d{6}\.(SZ|SH)$")
BAOSTOCK_SYMBOL_RE = re.compile(r"^(sz|sh)\.(\d{6})$")


def validate_internal_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if not INTERNAL_SYMBOL_RE.match(value):
        raise ValueError(
            f"unsupported A-share symbol {symbol!r}; expected like 000001.SZ or 600000.SH"
        )
    return value


def to_vendor_symbol(internal_symbol: str, source: str) -> str:
    source = _normalize_source(source)
    symbol = validate_internal_symbol(internal_symbol)
    code, exchange = symbol.split(".")
    if source == "baostock":
        prefix = {"SZ": "sz", "SH": "sh"}[exchange]
        return f"{prefix}.{code}"
    if source in {"akshare", "tushare"}:
        return symbol
    raise ValueError(f"unsupported source {source!r}")


def to_internal_symbol(vendor_symbol: str, source: str) -> str:
    source = _normalize_source(source)
    value = vendor_symbol.strip()
    if source == "baostock":
        match = BAOSTOCK_SYMBOL_RE.match(value)
        if not match:
            raise ValueError(
                f"unsupported baostock symbol {vendor_symbol!r}; expected like sz.000001"
            )
        exchange, code = match.groups()
        suffix = {"sz": "SZ", "sh": "SH"}[exchange]
        return f"{code}.{suffix}"
    if source in {"akshare", "tushare"}:
        return validate_internal_symbol(value)
    raise ValueError(f"unsupported source {source!r}")


def _normalize_source(source: str) -> str:
    value = source.strip().lower()
    if value not in SUPPORTED_SOURCES:
        raise ValueError(f"unsupported data source {source!r}")
    return value
