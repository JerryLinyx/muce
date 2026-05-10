from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from quant_backtest.data.cache import ParquetCache
from quant_backtest.data.constants import SOURCE_BAOSTOCK
from quant_backtest.data.providers import BaostockProvider


def main() -> None:
    parser = argparse.ArgumentParser(prog="quant-data")
    parser.add_argument("--cache-root", default="data/cache/a_share/daily")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download")
    _add_provider_args(download)
    download.add_argument("--start", required=True)
    download.add_argument("--end", required=True)
    download.add_argument("--all-symbols", action="store_true")
    download.add_argument("--as-of", help="universe date used with --all-symbols")
    download.add_argument("--batch-size", type=int, default=200)

    update = subparsers.add_parser("update")
    _add_provider_args(update)
    update.add_argument("--start", help="used only when no cache exists yet")
    update.add_argument("--end", required=True)
    update.add_argument("--all-symbols", action="store_true")
    update.add_argument("--as-of", help="universe date used with --all-symbols")
    update.add_argument("--batch-size", type=int, default=200)

    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--source", default=SOURCE_BAOSTOCK)
    inspect.add_argument("--adjust", default="qfq", choices=["raw", "qfq", "hfq"])
    inspect.add_argument("--symbols", default="")

    universe = subparsers.add_parser("universe")
    universe.add_argument("--source", default=SOURCE_BAOSTOCK)
    universe.add_argument("--as-of")
    universe.add_argument("--limit", type=int, default=0)

    args = parser.parse_args()
    cache = ParquetCache(Path(args.cache_root))

    if args.command == "download":
        _run_download(args, cache)
        return

    if args.command == "update":
        _run_update(args, cache)
        return

    if args.command == "inspect":
        symbols = _symbols(args.symbols) if args.symbols else None
        print(json.dumps(cache.inspect(source=args.source, adjust=args.adjust, symbols=symbols).as_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "universe":
        symbols = _provider(args.source).list_symbols(as_of=args.as_of)
        limited = symbols[: args.limit] if args.limit else symbols
        print(
            json.dumps(
                {
                    "source": args.source,
                    "as_of": args.as_of,
                    "symbol_count": len(symbols),
                    "symbols": limited,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return


def _add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", default=SOURCE_BAOSTOCK)
    parser.add_argument("--symbols", default="")
    parser.add_argument("--adjust", default="qfq", choices=["raw", "qfq", "hfq", "both"])


def _run_download(args: argparse.Namespace, cache: ParquetCache) -> None:
    provider = _provider(args.source)
    symbols = _resolve_symbols(args, provider)
    total_rows = 0
    adjusted: dict[str, dict[str, object]] = {}
    for adjust in _adjustments(args.adjust):
        rows, updated_symbols = _download_adjustment(
            provider,
            cache,
            symbols=symbols,
            start=args.start,
            end=args.end,
            adjust=adjust,
            batch_size=args.batch_size,
        )
        total_rows += rows
        adjusted[adjust] = _symbol_summary(rows, updated_symbols)
    print(
        json.dumps(
            {
                "rows": total_rows,
                "symbol_count": len(symbols),
                "adjustments": adjusted,
            },
            ensure_ascii=False,
        )
    )


def _run_update(args: argparse.Namespace, cache: ParquetCache) -> None:
    provider = _provider(args.source)
    symbols = _resolve_symbols(args, provider)
    total_rows = 0
    adjusted: dict[str, dict[str, object]] = {}
    for adjust in _adjustments(args.adjust):
        adjust_rows = 0
        updated_symbols = []
        for batch in _batches(symbols, args.batch_size):
            starts_by_symbol: dict[str, str] = {}
            for symbol in batch:
                last_date = cache.last_date(source=args.source, adjust=adjust, symbol=symbol)
                if last_date is None:
                    if not args.start:
                        raise SystemExit(f"--start is required for first update of {symbol}")
                    starts_by_symbol[symbol] = args.start
                else:
                    starts_by_symbol[symbol] = (last_date + timedelta(days=1)).strftime("%Y%m%d")

            # Different symbols can have different cache end dates, so updates stay symbol-granular.
            for symbol, start in starts_by_symbol.items():
                data = provider.get_daily_bars([symbol], start, args.end, adjust)
                if not data.empty:
                    cache.write(data)
                    adjust_rows += len(data)
                    updated_symbols.append(symbol)
        total_rows += adjust_rows
        adjusted[adjust] = _symbol_summary(adjust_rows, updated_symbols)
    print(json.dumps({"rows": total_rows, "symbol_count": len(symbols), "adjustments": adjusted}, ensure_ascii=False))


def _download_adjustment(
    provider: BaostockProvider,
    cache: ParquetCache,
    *,
    symbols: list[str],
    start: str,
    end: str,
    adjust: str,
    batch_size: int,
) -> tuple[int, list[str]]:
    total_rows = 0
    updated_symbols: list[str] = []
    for batch in _batches(symbols, batch_size):
        data = provider.get_daily_bars(batch, start, end, adjust)
        if not data.empty:
            cache.write(data)
            total_rows += len(data)
            updated_symbols.extend(sorted(data["symbol"].unique()))
    return total_rows, sorted(set(updated_symbols))


def _provider(source: str) -> BaostockProvider:
    if source != SOURCE_BAOSTOCK:
        raise SystemExit(f"provider {source!r} is not implemented in v1")
    return BaostockProvider()


def _resolve_symbols(args: argparse.Namespace, provider: BaostockProvider) -> list[str]:
    if args.all_symbols:
        symbols = provider.list_symbols(as_of=args.as_of)
    else:
        symbols = _symbols(args.symbols)
    if not symbols:
        raise SystemExit("no symbols resolved; provide --symbols or --all-symbols")
    return symbols


def _adjustments(value: str) -> list[str]:
    if value == "both":
        return ["qfq", "raw"]
    return [value]


def _batches(symbols: list[str], batch_size: int) -> Iterable[list[str]]:
    if batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")
    for start in range(0, len(symbols), batch_size):
        yield symbols[start : start + batch_size]


def _symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _symbol_summary(rows: int, symbols: list[str]) -> dict[str, object]:
    return {
        "rows": rows,
        "symbol_count": len(symbols),
        "symbol_sample": symbols[:10],
    }


if __name__ == "__main__":
    main()
