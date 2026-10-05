# Abstention gates ("işlem yapmamak da bir karardır")

Return `AKSİYON YOK`, `İZLE` or a smaller conditional setup when any gate fires. State which gate and what would reopen the decision.

| Gate | Fires when | Reopen when |
|---|---|---|
| Edge vs cost | Expected excess return ≤ round-trip cost + safety margin, or ≤ the deposit/money-market return for the horizon | Price improves or new evidence raises expected value |
| Width | P10–P90 range so wide that both the stop and the target sit inside normal noise | Volatility contracts or horizon lengthens |
| Disagreement | Strong families point opposite ways with no resolution | Catalyst resolves the conflict |
| Regime | Market regime is a downtrend and the stock lacks relative strength/independent catalyst | Follow-through day, breadth recovery, or stock-specific strength |
| Data | Stale, missing or conflicting decisive data (price, filing, corporate action) | Data verified |
| Event | Binary event inside the horizon that the model cannot price (court ruling, SPK decision, tender outcome) | Event passes or can be sized as a lottery-like bet |
| Liquidity | Planned size > ~2% of median daily value traded, VBTS measures, multi-tick spreads | Size reduced or liquidity improves |
| Calibration | Forecast ledger shows recent intervals too narrow (P10/P90 breaches well above 10% each) | Intervals widened; new sample recovers |

Thresholds are set before looking at outcomes and changed only with evidence from the ledger or `quant-research-lab`.

## Forecast ledger (performance monitor)

```bash
python scripts/forecast_ledger.py --ledger ~/Documents/borsa-kayit/forecast-ledger.jsonl add --ticker KOD --horizon-days 90 \
    --price 46.96 --p10 38 --p50 48 --p90 60 --target-price 56 --target-prob 0.3 --loss-threshold 0.10 --loss-prob 0.25 --action ADAY
python scripts/forecast_ledger.py --ledger ... due          # which forecasts matured
python scripts/forecast_ledger.py --ledger ... resolve --id <id> --price 51.2
python scripts/forecast_ledger.py --ledger ... score        # coverage, pinball vs random walk, Brier, hit rate
python scripts/forecast_ledger.py --ledger ... verify       # hash chain: detects edits
```

Statuses for a model or rule based on the ledger: `healthy` · `watch` (calibration drifting) · `restricted` (half size) · `abstain-only` · `retrain candidate` · `retire`. Never edit a past forecast; append a note instead.
