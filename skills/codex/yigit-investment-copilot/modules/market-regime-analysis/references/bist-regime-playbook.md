# BIST regime playbook (breadth, distribution, exposure)

`scripts/bist_breadth.py` measures; this page explains how to use the measurements.

## Axes to report

1. **Index trend:** XU100 vs SMA50/SMA200, SMA200 slope, distance from 52-week high; same in USD terms (XU100 ÷ USD/TRY).
2. **Breadth:** % of stocks above SMA50 and SMA200, % with SMA50 > SMA200, advancers/decliners, % near 52-week highs vs lows, median 1-month and 3-month returns.
3. **Pressure:** distribution days (index down ≥0.2% on higher volume) in the last 25 sessions; ≥5 means institutions are selling into strength.
4. **Turn signals:** follow-through day (≥1.5% gain on higher volume, day 4+ after an ≥8% correction low without undercutting the low). A follow-through day allows pilot buying; it fails often, so size small.
5. **Volatility:** 20-day realised volatility and its 1-year percentile.
6. **Rotation:** sector table by 3-month median return and % above SMA50; leaders vs laggards.
7. **Macro overlay:** TCMB policy and real rate, CPI trend, USD/TRY path, CDS, oil, global risk (VIX, DXY, US 10-year) from `macro_snapshot.py` and official releases.

## Heuristic regimes and exposure bands

| Regime | Conditions (typical) | Share of planned equity exposure | Risk per trade |
|---|---|---|---|
| Güçlü yükseliş | XU100 > SMA50 > SMA200, breadth > 60%, ≤4 distribution days | 80–100% | ~1.0% |
| Yükseliş | XU100 > SMA200, mixed breadth | 70–90% | 0.75–1.0% |
| Yükseliş — baskı altında | XU100 > SMA200 but ≥5 distribution days or breadth < 50% | 50–80% | ~0.75% |
| Düzeltme | XU100 < SMA50 but > SMA200 | 30–60% | ~0.5% |
| Dip arayışı / toparlanma denemesi | XU100 < SMA200 with follow-through day or improving breadth | 20–40% pilot | ~0.5% |
| Düşüş trendi | XU100 < SMA200 and SMA50 < SMA200, weak breadth | 0–30% (relative-strength or defensive names only) | 0.25–0.5% |

These bands are practitioner heuristics (O'Neil-style market direction, breadth thrust practice, exposure coaching), not optimised parameters. Always compare with the cash alternative: in Türkiye money-market funds and deposits can pay high nominal rates, so "wait in cash" has a real return.

## Regime-conditional factor behaviour (what to test, not assume)

- In strong uptrends, momentum and breakout setups tend to work better; in downtrends and high volatility, quality, low volatility and reversal-to-quality tend to hold up better. Verify on BIST with `quant-research-lab` before tilting weights.
- TL depreciation phases favour exporters and FX-revenue companies; disinflation with high real rates favours banks' margins after the repricing lag and hurts leveraged growth.
- Political or legal shocks cause correlated selling in liquid large caps first (foreign outflows); breadth collapses quickly and recovers only after policy responses.

## Report format

One line: regime + exposure band + risk per trade. Then axis table, conflicts (e.g. index up, breadth down), transition triggers (what would upgrade/downgrade the regime), and the implication for the user's horizon.
