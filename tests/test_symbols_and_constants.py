from __future__ import annotations

import pytest

from quant_backtest.data.constants import INTERNAL_ADJUST_TO_BAOSTOCK
from quant_backtest.data.symbols import to_internal_symbol, to_vendor_symbol


def test_baostock_adjust_mapping_is_locked() -> None:
    assert INTERNAL_ADJUST_TO_BAOSTOCK == {
        "hfq": "1",
        "qfq": "2",
        "raw": "3",
    }


@pytest.mark.parametrize(
    ("internal", "vendor"),
    [
        ("000001.SZ", "sz.000001"),
        ("600000.SH", "sh.600000"),
    ],
)
def test_baostock_symbol_round_trip(internal: str, vendor: str) -> None:
    assert to_vendor_symbol(internal, "baostock") == vendor
    assert to_internal_symbol(vendor, "baostock") == internal


@pytest.mark.parametrize("symbol", ["000001.XSHE", "600000.XSHG", "sz.000001"])
def test_rejects_unsupported_internal_symbol_aliases(symbol: str) -> None:
    with pytest.raises(ValueError):
        to_vendor_symbol(symbol, "baostock")
