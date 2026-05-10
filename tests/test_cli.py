from __future__ import annotations

import json
import sys

from quant_backtest.cli_backtest import main as backtest_main
import quant_backtest.cli_data as cli_data
from quant_backtest.cli_data import main as data_main
from quant_backtest.data.cache import ParquetCache
from tests.conftest import make_bars


def test_quant_data_inspect_cli(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-data",
            "--cache-root",
            str(tmp_path),
            "inspect",
            "--symbols",
            "000001.SZ",
            "--adjust",
            "qfq",
        ],
    )
    data_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["symbol_count"] == 1
    assert payload["adjust"] == "qfq"


def test_quant_data_universe_cli(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_data, "_provider", lambda source: FakeProvider())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-data",
            "universe",
            "--as-of",
            "20260507",
            "--limit",
            "1",
        ],
    )

    data_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["symbol_count"] == 2
    assert payload["symbols"] == ["000001.SZ"]


def test_quant_data_download_all_symbols_both_adjustments(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_data, "_provider", lambda source: FakeProvider())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-data",
            "--cache-root",
            str(tmp_path),
            "download",
            "--all-symbols",
            "--start",
            "20240102",
            "--end",
            "20240110",
            "--adjust",
            "both",
            "--batch-size",
            "1",
        ],
    )

    data_main()
    payload = json.loads(capsys.readouterr().out)
    cache = ParquetCache(tmp_path)
    assert payload["symbol_count"] == 2
    assert payload["adjustments"]["qfq"]["rows"] == 6
    assert payload["adjustments"]["raw"]["rows"] == 6
    assert cache.available_symbols(adjust="qfq") == ["000001.SZ", "600000.SH"]
    assert cache.available_symbols(adjust="raw") == ["000001.SZ", "600000.SH"]


def test_quant_backtest_validate_reads_qfq_signal_and_raw_execution(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=30))
    cache.write(make_bars("000001.SZ", adjust="raw", rows=30))
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-backtest",
            "--cache-root",
            str(tmp_path),
            "validate",
            "--symbols",
            "000001.SZ",
            "--strategy",
            "sma-cross",
            "--reports-dir",
            str(reports_dir),
        ],
    )
    backtest_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["signal_adjust"] == "qfq"
    assert payload["execution_adjust"] == "raw"
    assert payload["execution_timing"] == "next_open"
    assert payload["strategy"] == "sma-cross"
    assert payload["metrics"]["start_cash"] == 1_000_000
    assert payload["equity_rows"] == 30


def test_quant_backtest_validate_writes_report(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=30))
    cache.write(make_bars("000001.SZ", adjust="raw", rows=30))
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-backtest",
            "--cache-root",
            str(tmp_path),
            "validate",
            "--symbols",
            "000001.SZ",
            "--strategy",
            "sma-cross",
            "--reports-dir",
            str(reports_dir),
        ],
    )
    backtest_main()
    capsys.readouterr()  # discard
    val_dir = reports_dir / "validations"
    assert val_dir.exists()
    runs = [p for p in val_dir.iterdir() if p.is_dir()]
    assert len(runs) == 1
    assert (runs[0] / "manifest.json").exists()
    assert (runs[0] / "equity.parquet").exists()
    assert (runs[0] / "trades.parquet").exists()
    assert (runs[0] / "config.json").exists()


def test_quant_backtest_validate_no_report_flag_skips_write(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=30))
    cache.write(make_bars("000001.SZ", adjust="raw", rows=30))
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-backtest",
            "--cache-root",
            str(tmp_path),
            "validate",
            "--symbols",
            "000001.SZ",
            "--strategy",
            "sma-cross",
            "--no-report",
            "--reports-dir",
            str(reports_dir),
        ],
    )
    backtest_main()
    capsys.readouterr()
    assert not reports_dir.exists()


def test_quant_backtest_sweep_writes_report(tmp_path, monkeypatch, capsys) -> None:
    cache = ParquetCache(tmp_path)
    cache.write(make_bars("000001.SZ", adjust="qfq", rows=30))
    cache.write(make_bars("000001.SZ", adjust="raw", rows=30))
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quant-backtest",
            "--cache-root",
            str(tmp_path),
            "sweep",
            "--symbols",
            "000001.SZ",
            "--strategy",
            "sma-cross",
            "--fast-periods",
            "5",
            "--slow-periods",
            "20",
            "--reports-dir",
            str(reports_dir),
        ],
    )
    backtest_main()
    capsys.readouterr()
    sweeps_dir = reports_dir / "sweeps"
    assert sweeps_dir.exists()
    runs = [p for p in sweeps_dir.iterdir() if p.is_dir()]
    assert len(runs) == 1
    assert (runs[0] / "manifest.json").exists()
    assert (runs[0] / "results.parquet").exists()


class FakeProvider:
    def list_symbols(self, as_of: str | None = None) -> list[str]:
        return ["000001.SZ", "600000.SH"]

    def get_daily_bars(self, symbols: list[str], start: str, end: str, adjust: str):
        frames = [make_bars(symbol, adjust=adjust, rows=3) for symbol in symbols]
        import pandas as pd

        return pd.concat(frames, ignore_index=True)
