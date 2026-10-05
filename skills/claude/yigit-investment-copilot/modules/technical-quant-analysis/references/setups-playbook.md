# Setup playbook (what `technical_indicators.py` checks and how to use it)

Setups are conditions that historically organise entries and stops; none has a guaranteed edge on BIST. Combine with fundamentals, events and regime, and test before trusting any rule.

| Setup | Rule in the script | Typical use | Failure mode | BIST note |
|---|---|---|---|---|
| Trend template | Up to 8 criteria: price > SMA150/200, SMA150 > SMA200, SMA200 rising, SMA50 above both, price > SMA50, ≥30% above 52-week low, within 25% of 52-week high, beating XU100 over 6 months | Filter for stage-2 leaders (Minervini/O'Neil style) | Late-stage trends; momentum crashes after regime turns | Check USD-based chart; nominal TL trends can hide real declines |
| Weinstein stage | 150-day (≈30-week) average slope and price position | Stage 2 = favourable; stage 4 = avoid longs | Whipsaws near a flat average | Weekly closes reduce noise |
| Breakout ready | Close ≥97% of 55-day high, ATR(10)/ATR(50) < 0.85, 10/50-day volume < 1 | Buy-stop or limit just above the pivot on volume | False breakouts in weak markets | Limit-up gaps can skip entries; do not chase the queue |
| Breakout today | Close above 20-day high with volume ≥1.5× | Confirmation entry | Exhaustion breakouts after long runs | Prefer liquid names; check KAP for the cause |
| Pullback in uptrend | Close > SMA50 > SMA200, within 2% of EMA20, RSI 38–55 | Low-risk entry in an established trend | Pullback becomes a trend change | Stop under the swing low or SMA50 |
| Oversold in uptrend | Close > SMA200, RSI < 35 | Mean-reversion entry (supported by BIST reversal evidence at short horizons) | Falling knife when fundamentals changed | Require no negative KAP event; small size |
| Momentum burst | +4% day, closes in top quarter of range, volume ≥1.5× | Short swing (3–10 days) | Fades in thin stocks | Beware tavan/taban dynamics and news-driven gaps |
| VCP-like contraction | ATR(10)/ATR(50) < 0.7, within 10% of 52-week high, above SMA50 | Tight base before breakout | Contraction before breakdown in weak regimes | Needs market uptrend (regime) |
| Extended | Price > 1.25× SMA50 or RSI > 78 | Do not add; consider partial profits | Can stay extended in manias | Parabolic moves often reverse violently |
| Downtrend | Price < SMA200 and SMA50 < SMA200 | Avoid new longs except special situations | Late bear signals near bottoms | Wait for stage-1 base and follow-through day |

## From setup to plan

1. Identify the setup and the invalidation level (the point where the pattern is wrong).
2. Check liquidity and gap risk (ATR%, limit-day history, relative volume).
3. Run `trade-management-exits/scripts/trade_plan.py` for stop, size and targets.
4. Record the setup type in the journal; review hit rates by setup after enough trades.

## Multi-timeframe rule

Enter in the direction of the weekly trend (`weekly.trend_up`). Counter-trend trades need a reason (quality + oversold + catalyst) and half size.
