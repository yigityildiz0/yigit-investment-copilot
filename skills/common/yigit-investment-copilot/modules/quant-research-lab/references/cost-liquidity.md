# Cost and liquidity model (BIST)

## Cost stack per side

| Component | How to estimate | Notes |
|---|---|---|
| Broker commission | User's actual tariff (online rates differ widely by broker and account) | Ask; never assume the user's rate |
| BSMV | A percentage of commission (5% at the last check) | Verify current rate |
| Exchange / clearing pass-through | Broker statement | Often bundled |
| Half spread | (ask − bid)/2 ÷ mid; if unknown, one BIST price step | Thin names can have multi-tick spreads |
| Market impact | k · σ_daily · √(order ÷ daily value traded), k ≈ 0.5–1.0 | Square-root law; grows fast above 5–10% of ADV |
| Delay / missed fills | Price move between signal and execution | Limit orders reduce cost but add non-fill risk |

`cost_model.py` computes the stack, round-trip cost, break-even move and a capacity table.

## Practical limits

- Keep an order below ~1–2% of the stock's median daily value traded; above ~10% expect heavy impact and exit risk.
- In limit-up (tavan) or limit-down (taban) queues, fills are uncertain; a stop at a price during a limit-down day may not execute.
- VBTS measures (brüt takas, tek fiyat) reduce liquidity and trading frequency; include them in exit feasibility.
- Taxes: gains on BIST shares for resident individuals had 0% withholding at the last check; dividends 15% withholding since 22 Dec 2024. Verify current rules before using them.

## Report

Gross vs net return, cost per trade and per unit turnover, turnover per year, break-even cost, capacity table, and whether the edge survives 2× costs.
