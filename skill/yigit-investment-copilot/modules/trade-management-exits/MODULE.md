# Module: trade-management-exits

> Part of the `yigit-investment-copilot` skill. Paths below are relative to this module folder (`modules/trade-management-exits/`).
> Original trigger scope: Turn an approved idea into a written trade plan and manage it until exit: entry method and order type on Borsa İstanbul, structure/ATR stops, R-multiples, targets, partial profit-taking, trailing and time stops, event rules, adding/reducing, and sell decisions for winners and losers. Use for "stop nereye koyayım", "ne zaman satayım", "kâr alayım mı", "zararda tutayım mı", "ekleme yapayım mı", "hedef fiyat", "emir tipi", "kaç lot", or when a position needs a review. Never places orders; the user executes at their broker.

# Trade Management and Exits

Selling well matters as much as buying well: most retail damage comes from letting losers run, selling winners too early and trading without a plan. Read [references/exit-playbook.md](references/exit-playbook.md) for the decision tree and `../turkey-markets-analysis/references/bist-market-mechanics.md` for sessions, price steps, limits and order types.

## Build the plan (before entry)

Run:

```bash
python scripts/trade_plan.py --entry 46.96 --history ~/.cache/yigit-investment-copilot/chart/KRDMD.csv \
    --capital 500000 --risk-pct 1 --horizon-days 60 --md plan.md
```

(`--history` takes any OHLCV CSV from `price_history.py`; `borsa.py ticker KOD` fills that cache. Without history pass `--atr` and optional `--stop`/`--targets`.)

It returns stop (structure below swing support, else 2×ATR, rounded to BIST steps), R per share, quantity (risk- vs budget-limited, lot = 1), cash used, modeled loss at stop, loss if a −10% gap jumps the stop, R-multiple targets plus resistance levels, and management rules. Check the warnings (stop too wide/narrow, weak reward/risk).

Plan contents that must be written down:

1. **Thesis and horizon** (from the committee) and the kill condition that is not price-based.
2. **Entry method.** Limit at or near a planned level; staged entries (e.g. ½ now, ½ on confirmation); avoid market orders in thin books and avoid chasing a limit-up (tavan) queue.
3. **Initial stop and size.** Size from the stop, never the stop from the size. Risk per trade 0.25–1% of capital depending on regime and conviction; speculative budget capped separately.
4. **Targets.** R-multiples (1.5R, 2R, 3R) and nearest resistances; first profit-take no closer than 1.5R unless the thesis is time-boxed.
5. **Management.** Move stop to break-even after +1R close; take ⅓ at the first target; trail the rest (chandelier = 22-day high − 3×ATR, or close below EMA20/SMA50 depending on horizon); time stop if +0.5R is not reached within about a third of the horizon.
6. **Events.** Before earnings, genel kurul, bonus/rights dates or TCMB/TÜİK releases: keep only the size you can hold through a gap, or reduce.
7. **Alerts.** Price alerts at stop, break-even trigger and targets in the broker app; review date in the thesis tracker.

## Manage and exit (after entry)

Apply the exit playbook in order: thesis break → stop → regime change → time stop → target/valuation → better opportunity → rebalancing/concentration. Record every exit with the reason in the journal.

Monitor open positions and the watchlist from a CSV (`code,entry,stop,target1,target2,quantity,review_date,thesis`):

```bash
python scripts/watchlist_monitor.py --watchlist izle.csv --kap-days 3 --out izle
```

It flags stop breached or within 3%, targets reached, +1R (move the stop to break-even), close below SMA50/SMA200, sharp daily moves, earnings within 7 days, ex-dividend within 10 days, review date passed and new important or negative KAP disclosures, sorted by urgency with the plan action for each. The flags follow the user's written plan; they are not orders. Adding: only to a position that is working (above entry, thesis intact), never averaging down on a losing trade unless it was planned as a staged value entry with a total loss cap.

## BIST execution notes

- Opening auction 09:40–10:00 and closing session 18:00–18:10 set reference prices; large gaps happen at the open after KAP news released outside hours.
- Daily limit ±10%: a stop can be skipped by a limit-down open; size for that gap, not only for the stop distance.
- Stocks under VBTS measures (brüt takas, tek fiyat) trade less often; exits take longer.
- T+2 settlement: sale proceeds are usable for new buys the same day at most brokers but withdrawable after settlement; check your broker.
- Conditional orders (stop-loss/take-profit) are broker features, not exchange guarantees; verify behaviour at your broker.

## Hard rules

- No plan, no trade: entry, stop, size, targets and kill condition must exist before the order.
- Never widen a stop after entry to avoid a loss; tightening is allowed.
- Never let a speculative position grow into a core holding without a new thesis.
- Never place, transmit or automate orders; never ask for broker credentials.
