# System Capabilities

## Data Layer

- Download daily OHLCV bars from Baostock (raw, qfq, hfq adjustment modes)
- Parquet cache partitioned by source, adjust, symbol
- Incremental cache updates
- Cache inspection with row counts, quality reports
- Internal symbol format (000001.SZ), vendor conversion
- Optional DuckDB query layer over Parquet partitions
- Full-market batch download (5200 symbols, 2.5M rows, 245MB)

## Feature Layer

- Pure-Python technical indicators: SMA, EMA, MACD, RSI, KDJ, Bollinger Bands, ATR, OBV, Volume MA
- TA-Lib as optional oracle for comparison
- Per-symbol indicator computation
- Cross-validated against VectorBT for MA/EMA/Bollinger/MACD

## Backtest Layer

### VectorBT Engine
- Fast parameter sweeps with grid expansion
- Three strategies: SMA cross, three-rising-hold-one, three-falling-buy-three-rising-sell
- Pyramiding support (from_orders, max_position_percent)
- Risk-control parameters: stop-loss, take-profit, max hold days
- Integer share granularity (size_granularity=1)
- Rank by total_return, sharpe, max_drawdown, or trade count

### Backtrader Engine
- Event-driven validation with realistic order execution
- Dual price view: qfq signal lines + raw execution lines
- Custom A-share pandas feed
- Built-in SMA cross, three-rising, three-falling strategies
- Equity, orders, and trades analyzers
- Precomputed selector strategy
- Signal-adjusted entry_bar tracking

## Selection Layer

### Daily Selector
- Full-market candidate scanning across 5200 A-share stocks
- Six technical factors: ma_breakout, kdj_golden_cross, macd_golden_cross, rsi_momentum, volume_breakout, boll_breakout
- Factor scoring (additive vote model)
- Hard filters: require_factors, exclude_factors
- Top-N ranking by score, amount, volume

### Hit-Rate Validation
- Forward-return hit-rate analysis (close-to-next-close, next-open-to-next-close)
- Daily and overall win rate statistics
- Factor attribution analysis
- Parameter sweep over min_score, top_n, factor thresholds

### Execution Simulation
- Entry lag days (model next-day execution)
- Lot-size rounding (100-share lots)
- Commission, base slippage, surge slippage
- Limit-up buy rejection, limit-down sell rejection
- Stop-loss and take-profit
- Fixed holding days
- Position sizing by target percentage
- Open/close entry and exit field selection
- Parameter sweeps with layered factor grids

### Backtrader Validation
- Validate precomputed selector candidates through Backtrader
- Per-date ordered candidate list with selector ranking preserved
- Lot-size sizing, explicit close orders for exit
- entry_bar recorded on completed fill
- Limit-up/limit-down-aware entry logic

### Diagnostics
- Simulator vs Backtrader side-by-side comparison
- Order-level divergence detection
- Equity curve comparison
- Divergence categorization (sizing, symbol selection, fill price, etc.)
- Structured artifact export

## API Layer

- FastAPI server with read-only endpoints
- Four routers: system, data, selection, reports
- Job-based selection with SSE progress streaming
- Result cache by config hash + date + universe
- RFC 7807 error envelope
- In-process JobRegistry (TTL 1h)
- Reports served from disk artifacts (manifest.json + parquet)
- CORS preflight allowed for `localhost:3000` (Next.js) and `localhost:5173` (Vite) by default; override via `MUCE_API_CORS_ORIGINS` env var

## Reports

- Structured on-disk format: reports/sweeps/{run_id}/ and reports/validations/{run_id}/
- Manifest with git provenance, config, metrics
- Equity, orders, trades as Parquet artifacts
- CLI --no-report to opt out, --reports-dir to redirect

## Gaps

- No unified Portfolio/Broker/Order/Fill model (P0-4)
- No complete A-share market rules engine (P0-5)
- No persisted feature/factor cache (P0-6)
- No multi-year data (only 1 year) (P1-1)
- No factor IC/RankIC evaluation (P1-2)
- No walk-forward validation (P1-3)
- No standardized research artifact layout (P1-4)
- No minute data or tail-close validation (P2-1)
- No paper trading architecture (P2-2)
- No centralized risk control layer (P2-3)