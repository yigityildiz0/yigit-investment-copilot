# Forecast method

## Evidence stack

1. Verified current price and product identity
2. Point-in-time adjusted historical distribution and matched regimes
3. Options/implied information when liquid and available
4. Fundamentals, valuation and consensus dispersion
5. Dated catalyst/event probabilities
6. Macro, sector and technical regime
7. Execution, liquidity, spread, time decay and leverage

## Horizon weighting

- Days to a few weeks: volatility, market regime, liquidity, technical structure and dated events dominate; directional drift is heavily shrunk.
- Months: add earnings path, estimate revisions, valuation and sector/macro transmission.
- Years: business economics, reinvestment, balance sheet, dilution, valuation and regime change dominate; short-term technical indicators carry little weight.

## Distribution construction

Use at least two views when data permits:

- Parametric range from annualized volatility and a conservative drift.
- Empirical rolling-horizon distribution from adjusted point-in-time history.

Add separate event branches when a binary or discontinuous catalyst exists. Do not average mutually exclusive product outcomes into one smooth target without showing the branches.

## Candidate ranking

Use a transparent table containing median return, probability of profit, probability of exceeding the target, expected downside, severe-loss probability, liquidity/spread, catalyst quality, invalidation and confidence. Avoid composite scores unless weights are visible.

## Probability meaning and abstention

`forecast_ranges.py` outputs `probability_terminal_at_or_above_target`: the
probability of ending the horizon above the target under the stated model. It
does not estimate touching the target at any time. Historical frequencies use a
single consistent adjusted price basis and completed bars; overlapping windows
are not independent samples. Both outputs are explicitly uncalibrated. Never
translate a lane/composite score into a success probability or invent confidence
percentages. If the event, price basis, measured volatility, sample provenance or
calibration is unavailable, mark it unavailable or present a clearly conditional
scenario; do not supply a default 40% volatility or +10% target as observed data.
