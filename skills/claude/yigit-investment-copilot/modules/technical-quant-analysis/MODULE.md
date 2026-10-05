# Module: technical-quant-analysis

> Part of the `yigit-investment-copilot` skill. Paths below are relative to this module folder (`modules/technical-quant-analysis/`).
> Original trigger scope: Perform evidence-based technical and quantitative analysis from verified OHLCV data, including trend, momentum, volatility, volume, support/resistance, multi-timeframe structure, scenario levels, position risk, strategy testing, and backtest quality control. Use when the user asks for chart analysis, RSI/MACD/ATR, entry or exit timing, short-term price scenarios, stop/invalidation levels, technical screening, or whether a signal historically worked. Do not use technical indicators alone to claim certainty or replace fundamental, event, liquidity, and product-risk analysis.

# Technical Quant Analysis

Use indicators as measurements, not prophecies. Read [references/data-contract.md](references/data-contract.md), [references/interpretation.md](references/interpretation.md), and for strategy testing [references/backtest-standard.md](references/backtest-standard.md).

## Workflow

1. Verify instrument, exchange, currency, timezone, interval, data source, fetch time, delay, and corporate-action adjustment.
2. Exclude incomplete candles. Reject duplicated, unordered, non-positive, or internally inconsistent OHLCV rows.
3. Run `scripts/technical_indicators.py <csv> --benchmark XU100.csv --horizon-days N --repair --md ta.md` on sufficient data (≥60 candles; ≥252 for 52-week and 200-day measures). It adjusts OHLC by adj_close, and returns trend/momentum/volatility/volume indicators, ADX/DMI, Bollinger, OBV, MFI, swing support/resistance clusters, relative strength and beta vs the benchmark, weekly trend, rule-based setups (see [references/setups-playbook.md](references/setups-playbook.md)) and ATR/chandelier/volatility scenario levels. Do not report unavailable long-window indicators as if calculated.
4. Classify regime: trend, range, breakout, breakdown, volatility expansion/contraction, and liquidity quality.
5. Inspect price structure, moving averages, RSI, MACD, ATR, volume, gaps, and multi-timeframe agreement. Avoid indicator-count voting.
6. Express entry zone, invalidation, targets, and risk/reward as scenarios tied to confirmed levels and execution costs.
7. Combine with fundamentals, valuation, macro, catalysts, and product mechanics when the decision is an investment rather than a chart exercise.
8. For historical performance claims, require a point-in-time backtest packet and run `scripts/backtest_audit.py` before interpreting results; to test a rule yourself use `quant-research-lab` (walk-forward, costs, Deflated Sharpe).

## Hard rules

- Never calculate from a screenshot when raw dated prices can be obtained.
- Never mix adjusted and unadjusted prices across splits, dividends, rights issues, or contract rolls.
- Never use an unfinished candle to confirm a close-based signal.
- Never call overbought an automatic sell or oversold an automatic buy.
- Never optimize on the full sample and report the same sample as validation.
- Include fees, spread, slippage, taxes, latency, delistings, survivorship bias, look-ahead, and data revisions where relevant.
- Distinguish exploratory signals from independently validated strategies.

## Output

Report data timestamp and quality first, then regime, decisive levels, indicator readings, bull/base/bear paths, invalidation, modeled risk, and confidence. Say what evidence would confirm or reject the setup. Do not output a naked BUY/SELL score.
