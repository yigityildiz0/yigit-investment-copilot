# Module: probabilistic-market-forecast

> Part of the `yigit-investment-copilot` skill. Paths below are relative to this module folder (`modules/probabilistic-market-forecast/`).
> Original trigger scope: Estimate realistic price and return ranges, target probabilities, downside probabilities, and probability-weighted scenarios for stocks, funds, ETFs, futures, warrants, crypto, commodities, FX, and portfolios. Use when the user asks how much an instrument may rise or fall, what it may be worth after days/weeks/months, which candidate has the highest realistic upside, the chance of reaching a target, or requests a forecast rather than only descriptive analysis. Combine base rates, adjusted historical volatility, current regime, valuation/fundamentals, catalysts, technical structure, liquidity and implied information; track calibration and avoid single-point certainty.

# Probabilistic Market Forecast

Forecast a distribution, not a story. Give the user the most realistic actionable estimate the evidence supports, including high-risk opportunities when requested.

Read [references/forecast-method.md](references/forecast-method.md) and [references/calibration.md](references/calibration.md). Combine evidence with [references/multi-signal-ensemble.md](references/multi-signal-ensemble.md) and apply [references/abstention-gates.md](references/abstention-gates.md) before any action. Log every actionable forecast with `scripts/forecast_ledger.py` (append-only, hash-chained) and score it at maturity.

## Workflow

1. Resolve instrument, venue, currency, current executable price, data timestamp, horizon and target event.
2. For an open-ended “which stock has the best upside?” request, use `equity-opportunity-funnel` module first and forecast only the properly shortlisted finalists. Do not rank a few convenient tickers and imply a market-wide search.
3. Obtain adjusted point-in-time history and enough observations for the horizon. Measure volatility, drawdowns, skew, gaps, liquidity and regime dependence.
4. Run `scripts/forecast_ranges.py` for a transparent parametric range and, when a history CSV is available, empirical rolling-horizon base rates. For the outside view of a setup across the whole universe run `scripts/base_rates.py --history-dir <histories> --horizon-days <h>` (or `python scripts/borsa.py taban --horizon <h>` from the skill root): forward-return distributions after trend-template, 52-week-high, breakout, momentum-decile, oversold-uptrend, 1-month-drop and limit-up-streak states versus the same-day baseline, by year, plus today's matches. Survivorship and overlap caveats are printed with the numbers.
5. Add current information that a pure price model misses:
   - Fundamentals, valuation and what is priced in
   - Earnings, legal, policy, unlock or other dated catalysts
   - Macro and sector regime
   - Technical structure and volatility regime
   - Bid/ask, depth, funding, time decay and product mechanics
6. Build bear, base and bull cases with conditional probabilities. Use an event mixture when a catalyst makes the return distribution discontinuous.
7. Shrink uncertain drift toward zero or the relevant benchmark, especially at short horizons. Let volatility dominate when evidence for directional edge is weak.
8. Compare candidates using probability-weighted return, probability of loss, tail loss, liquidity, catalyst and invalidation—not maximum theoretical upside alone.
9. Record dated forecasts in the ledger (`scripts/forecast_ledger.py add --thesis "..." --kill "..." --benchmark-price <XU100>`) and score them after maturity (`resolve --benchmark-price --lesson "..."`, `score`; `scripts/score_forecasts.py` still scores ad-hoc binary lists). Before re-analysing a name read `forecast_ledger.py history --ticker KOD` (past calls, excess return versus the index, lessons); `history --lessons-only` is the memory to carry into the next committee. Tighten or widen future confidence based on calibration; a model that does not beat the random-walk benchmark gets `restricted` or `abstain-only` status.

## Required forecast

Return:

- Current price, source, timestamp and delay
- Horizon and model/data cutoff
- P10, P25, P50, P75 and P90 price or return ranges
- Probability of reaching the user's target
- Probability of losing more than the stated threshold
- Bear/base/bull scenarios and conditions
- Expected return range and tail-risk caveat
- Entry gate, invalidation, size input and monitoring trigger
- Confidence level and which evidence most changes the estimate

Use rounded ranges that match evidence quality. Do not print fake precision from a fragile model.

## High-risk requests

- Do not replace the forecast with “do not invest.” If the user accepts the full stated loss, show the strongest positive-asymmetry setup and alternatives.
- Explicitly distinguish `highest possible upside` from `highest probability-weighted upside` and recommend from the latter unless the user asks for a lottery-like payoff.
- For lottery-like requests, show probability of near-total loss and break-even probability, then provide the best structured candidate if a defensible one exists.
- If no positive edge is detectable, say `no edge`; if the user still wants a trade, provide the least-bad conditional setup and label it accurately.

## Model limits

Historical and lognormal ranges understate some event, liquidity and leverage tails. Warrants require time, implied volatility, delta, ratio and issuer quotes; futures require margin and mark-to-market; funds use dated NAV rather than intraday execution. Never map an underlying forecast mechanically to a derivative return without product-specific modeling.
