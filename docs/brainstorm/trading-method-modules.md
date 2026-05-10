# Brainstorm: Trading Method Modules

## Context

This document organizes the trading modes from the reference image into implementable modules for the A-share quant research system.

Source modes:

```text
技术指标
市场情绪
均线系统
龙头战法
内幕信息
筹码峰
资金流
K线形态 + 成交量
宏观政策分析
基本面分析
互联网战法
```

## Design Rule

Each mode must become a testable module, not a vague trading idea.

For every module we should define:

- data inputs
- feature/factor outputs
- signal rules
- validation method
- known risks
- implementation priority

No module should be allowed into strategy sweep until its data source, feature definition, and validation semantics are explicit.

## Module Map

| Module | Source Mode | Primary Layer | Priority | Current Status |
|---|---|---:|---:|---|
| Technical Indicator Engine | 技术指标 | Feature | P0 | Partially implemented |
| Moving Average System | 均线系统 | Factor / Strategy | P0 | Partially implemented |
| K-Line And Volume Pattern Engine | K线形态 + 成交量 | Factor / Selector | P0 | Partially implemented |
| Market Sentiment Engine | 市场情绪 | Market Regime / Factor | P1 | Not implemented |
| Capital Flow Engine | 资金流 | Factor | P1 | Not implemented |
| Fundamental Analysis Engine | 基本面分析 | Factor | P1 | Not implemented |
| Macro Policy Engine | 宏观政策分析 | Regime / Event | P2 | Not implemented |
| Leading Stock Strategy Engine | 龙头战法 | Selector / Strategy | P2 | Not implemented |
| Chip Distribution Engine | 筹码峰 | Feature / Factor | P2 | Not implemented |
| Internet Narrative Engine | 互联网战法 | Sentiment / Event | P3 | Not implemented |
| Insider Information | 内幕信息 | Excluded / Compliance | Not allowed | Do not implement as trading input |

## P0 Modules

### 1. Technical Indicator Engine

Purpose:

- Provide standardized, reproducible technical indicators.

Included features:

```text
MA
EMA
MACD
KDJ
RSI
BOLL
ATR
VOL_MA
OBV
MFI
```

Data required:

- Daily OHLCV.
- `qfq` for signal features.
- `raw` for execution validation.

Current status:

- Basic indicator layer already exists.
- Still needs persisted feature cache and external-library comparison tests.

Acceptance criteria:

- Indicator formula, parameters, warmup behavior, and missing-value policy are documented.
- Feature outputs can be persisted and inspected.
- At least one optional external library comparison exists for MACD/RSI/BOLL.

### 2. Moving Average System

Purpose:

- Model trend-following and trend-filter conditions.

Example factors:

```text
MA short > MA long
close crosses above MA
MA slope > 0
price above multiple MA lines
MA compression then expansion
```

Data required:

- Daily qfq OHLCV.

Validation:

- Hit-rate by forward return.
- VectorBT parameter sweep.
- Backtrader validation for selected rules.

Risks:

- Late signals in sideways markets.
- High whipsaw risk.

Acceptance criteria:

- MA rules are parameterized.
- Sweep can test window combinations.
- Results include turnover and drawdown, not only return.

### 3. K-Line And Volume Pattern Engine

Purpose:

- Detect price/volume structures such as breakouts, reversals, and volume confirmation.

Example factors:

```text
large bullish candle
large bearish candle
breakout with volume
shrinking volume pullback
gap up / gap down
three rising / three falling
long upper shadow
long lower shadow
```

Data required:

- Daily OHLCV.
- Eventually minute data for intraday confirmation.

Current status:

- Simple three-rising / three-falling MVP exists.
- Volume breakout factor exists in selector.

Acceptance criteria:

- Each pattern has a precise formula.
- Pattern labels can be inspected per symbol/date.
- Strategy tests separate signal close, next open, and close-to-close assumptions.

## P1 Modules

### 4. Market Sentiment Engine

Purpose:

- Estimate broad market risk appetite and short-term trading heat.

Example features:

```text
涨停家数
跌停家数
炸板率
连板高度
上涨家数 / 下跌家数
成交额变化
指数位置
北向/主力流 proxy if available
```

Data required:

- Full-market daily raw data.
- Limit-up/limit-down detection.
- Index data.
- Trading calendar.

Validation:

- Regime-split strategy results.
- Compare factor performance in high/low sentiment regimes.

Acceptance criteria:

- Daily sentiment table can be generated.
- Selector can use sentiment regime as a filter.
- Reports show strategy performance by sentiment bucket.

### 5. Capital Flow Engine

Purpose:

- Capture money-flow and liquidity preference.

Example features:

```text
成交额排名
成交额放大
量价齐升
大单资金流 if available
主力净流入 if available
turnover
volume-price divergence
```

Data required:

- Daily amount/volume.
- Turnover and float shares if available.
- Optional provider-specific money-flow data.

Validation:

- Factor IC / RankIC.
- Quantile return.
- Liquidity-filtered selector backtests.

Risks:

- Provider money-flow fields may be black-box and inconsistent.
- Volume can represent both accumulation and distribution.

Acceptance criteria:

- Start with transparent OHLCV-derived flow proxies.
- Treat provider money-flow data as optional and source-tagged.

### 6. Fundamental Analysis Engine

Purpose:

- Add medium-term stock quality and valuation filters.

Example features:

```text
PE
PB
PS
ROE
revenue growth
net profit growth
gross margin
debt ratio
cash flow quality
market cap
industry classification
```

Data required:

- Financial statements.
- Valuation snapshots by date.
- Industry classification.
- Market cap and float market cap.

Validation:

- Monthly or quarterly rebalance tests.
- Factor IC and quantile returns.
- Industry/market-cap neutral analysis.

Risks:

- Financial data must be point-in-time safe.
- Announcement-date and restatement handling matter.

Acceptance criteria:

- No fundamental factor is used unless its availability date is known.
- Reports separate announcement date and report period.

## P2 Modules

### 7. Macro Policy Engine

Purpose:

- Model macro and policy regime impacts.

Example features/events:

```text
interest rate changes
reserve requirement ratio changes
major policy meetings
industry policy announcements
fiscal stimulus
exchange rate regime
commodity shocks
```

Data required:

- Macro time series.
- Policy event calendar.
- Sector mapping.

Validation:

- Event study.
- Regime-split backtests.

Risks:

- Hard to quantify.
- High risk of narrative fitting.

Acceptance criteria:

- Events must have timestamp, source, affected sectors, and rule-based encoding.

### 8. Leading Stock Strategy Engine

Purpose:

- Identify market leaders in hot themes or sectors.

Example features:

```text
sector-relative strength
recent high breakout
limit-up sequence
highest turnover in sector
market cap / liquidity filter
theme membership
leader-follower spread
```

Data required:

- Sector/theme classification.
- Limit-up history.
- Relative strength.
- Full-market daily data.

Validation:

- Daily selector backtests.
- Sector-level attribution.
- Liquidity and limit-up feasibility checks.

Risks:

- Strong survivorship and narrative bias.
- Requires reliable theme classification.

Acceptance criteria:

- Must define leader selection mechanically.
- Cannot rely on manual post-hoc theme labels.

### 9. Chip Distribution Engine

Purpose:

- Approximate cost distribution and support/resistance zones.

Example features:

```text
volume-at-price approximation
cost concentration
profit-holder ratio
chip peak near current price
break above high-volume cost zone
```

Data required:

- At least daily OHLCV for approximation.
- Prefer minute data for better price-volume distribution.

Validation:

- Compare daily approximation versus minute-derived version on sampled symbols.
- Test breakouts above cost concentration zones.

Risks:

- True holder cost distribution is not directly observable.
- Daily approximations can be misleading.

Acceptance criteria:

- Clearly label this as an approximation.
- Formula must be reproducible and not imply access to true holder data.

## P3 Modules

### 10. Internet Narrative Engine

Purpose:

- Capture public online attention and narrative momentum.

Example features:

```text
search trend
news count
social-media mention count
sentiment score
theme keyword burst
forum heat
```

Data required:

- News/search/social data.
- Timestamped articles/posts.
- Symbol/theme entity mapping.

Validation:

- Event-time hit rate.
- Decay analysis.
- False-positive review.

Risks:

- High noise.
- Data licensing and scraping compliance.
- Easy to overfit.

Acceptance criteria:

- Public-data only.
- Source and timestamp must be stored.
- Must include decay analysis.

## Excluded Module

### 11. Insider Information

Decision:

- Do not implement insider information as a trading signal.

Reason:

- It is not a compliant or reproducible data source.
- It cannot be safely validated as a systematic research input.

Allowed substitute:

```text
公告事件
监管披露
大宗交易
龙虎榜
股东增减持公告
机构调研公告
新闻事件
```

These must come from public, timestamped, auditable sources.

## Suggested Build Order

1. Finish P0 technical modules:
   - Technical Indicator Engine
   - Moving Average System
   - K-Line And Volume Pattern Engine

2. Add market-wide context:
   - Market Sentiment Engine
   - Capital Flow Engine

3. Add slower-moving filters:
   - Fundamental Analysis Engine

4. Add advanced event/regime modules:
   - Macro Policy Engine
   - Leading Stock Strategy Engine
   - Chip Distribution Engine

5. Add narrative data last:
   - Internet Narrative Engine

## Integration With Current System

Each module should integrate through the same pipeline:

```text
Data Provider
  -> Standardized Cache
  -> Feature Engine
  -> Factor Table
  -> Selector / Strategy
  -> Fast Sweep
  -> Backtrader Validation
  -> Diagnostics
  -> Report
```

The immediate next module work should not start by adding more strategy rules. It should first improve the feature/factor cache and engine validation so these modules can be tested systematically.

