# Multi-signal forecast (evidence-weighted, not vote-counting)

Combine independent information families; quantify disagreement; never let one indicator or one story set the number.

## Signal families

1. Fundamentals and earnings direction (quality, revisions, surprises)
2. Valuation vs peers/history and what the price implies
3. Price/volume state (trend, momentum, volatility, relative strength)
4. Events and text (KAP, guidance, contracts, capital actions)
5. Macro/regime and sector transmission
6. Flow and positioning (where data exists)
7. Catalyst timing within the horizon

## Procedure

1. For each family write: sign (+/0/−), strength (1–3), freshness, evidence quality (A/B/C) and the channel through which it affects the price in this horizon.
2. Start from the **base rate**: the unconditional return distribution for the horizon (volatility-based range from `forecast_ranges.py`, the stock's own rolling-horizon history, and the index/sector history). Shrink drift toward zero or toward the deposit/benchmark rate, strongly at short horizons.
3. Adjust the centre only for families with strength ≥2 and quality A/B; adjust the width for disagreement and event risk (widen when families conflict, when a binary event is inside the horizon, or when liquidity is thin).
4. Prefer simple, interpretable weights (equal or evidence-quality weights). Learned or optimised weights are allowed only when `quant-research-lab` shows they beat simple weights out of sample after costs.
5. Express the result as P10/P50/P90, probability of reaching the target, probability of losing more than the threshold, and bear/base/bull branches when an event creates discontinuity.
6. Run the abstention gates (below). Log the forecast before acting.

## Disagreement table (include in detailed answers)

| Family | Sign | Strength | Quality | Horizon relevance | Note |
|---|---|---|---|---|---|

Agreement among families that share the same data (e.g. several price indicators) counts once.
