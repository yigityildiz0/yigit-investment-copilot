# Module: turkey-markets-analysis

> Part of the `yigit-investment-copilot` skill. Paths below are relative to this module folder (`modules/turkey-markets-analysis/`).
> Original trigger scope: Analyze Turkish financial markets using BIST, KAP, TEFAS, TCMB EVDS, TÜİK, SPK, issuer and fund documents. Use for BIST stocks, Turkish ETFs or certificates, TEFAS funds, TRY and FX macro effects, inflation accounting, dividends and corporate actions, VİOP futures/options, warrants, İş Bankası product questions, Turkish market mechanics, and short-horizon Turkish investment decisions. Produce current-source evidence, fundamental and fund analysis, macro transmission, leveraged-product risk, scenarios, and clear AL/TUT/AZALT/SAT/İZLE outputs. Do not use for non-Turkish markets unless comparing them with Türkiye.

# Turkey Markets Analysis

Use official Turkish sources first and label every live figure with date, time, currency, and delay status.

Read only the relevant reference:

- BIST equity: [references/bist-equity.md](references/bist-equity.md)
- Exchange mechanics (sessions, ±10% limit, price steps, VBTS, T+2, orders, taxes, corporate actions): [references/bist-market-mechanics.md](references/bist-market-mechanics.md)
- TEFAS fund: [references/tefas-funds.md](references/tefas-funds.md)
- Türkiye macro: [references/macro-regime.md](references/macro-regime.md) and the sector map [references/turkey-transmission-map.md](references/turkey-transmission-map.md)
- VİOP or warrants: [references/leveraged-products.md](references/leveraged-products.md)
- Source routing: [references/turkey-sources.md](references/turkey-sources.md); live data scripts live in `market-data-engine`.

## Workflow

1. Verify code, instrument class, issuer/founder, currency, and market. Stop on OCR or code ambiguity.
2. Identify whether the decision is new buy, add, hold, reduce, sell, hedge, or compare and establish the horizon.
3. For an open-ended BIST stock recommendation or alternatives request, use `equity-opportunity-funnel` module to scan the broad eligible universe and progressively deepen finalists. Do not generate a final action from a handful of familiar BIST names.
4. Gather the minimum current official evidence, then add market data and independent corroboration. With a shell and internet, `python scripts/borsa.py ticker KOD` (skill root) collects price history, technicals, KAP and statements in one run; otherwise browse the primary pages.
5. Normalize accounting period, consolidation basis, TMS 29 inflation treatment, corporate actions, fund category, NAV date, and benchmark.
6. Use `$public-equity-investing` for deep listed-company valuation, earnings, thesis, catalysts, and portfolio-risk workflows.
7. Use `technical-quant-analysis` module when price timing or chart evidence matters.
8. Use `probabilistic-market-forecast` module for realistic price ranges, target probabilities, and high-upside candidate ranking.
9. Use `scripts/fund_metrics.py` for fund return/risk calculations and `scripts/leveraged_scenarios.py` for transparent VİOP or warrant scenario math.
10. Use `finance-evidence-guard` module before quoting a live price, NAV, fee, tax/legal rule, or current filing number.
11. Give a clear action, bear/base/bull cases, invalidation, liquidity/cost constraints, and confidence.

## Hard rules

- Do not describe Borsa İstanbul's delayed public web data as real-time.
- Do not infer a public KAP or TEFAS API merely because an unofficial scraper exists.
- Do not analyze a fund code until the exact fund is confirmed.
- Do not compare TEFAS funds from return alone; include holdings, mandate, fee, benchmark, risk, drawdown, liquidity/valuation timing, and category consistency.
- Do not compare nominal revenue or profit across high-inflation periods without checking reporting basis and real effects.
- Do not invent an exact VİOP or warrant quantity before contract terms, executable price, fees, budget, and loss boundary are verified. Until then, give a conditional shortlist, price gate and quantity formula rather than ending the analysis.
- Do not imply that a stop order guarantees the modeled loss.
- Do not reject an informed legal high-risk trade merely for being high risk. Rank the strongest setup and alternatives, quantify the full-loss or margin risk once, and provide an executable plan when inputs are available.
- Do not label a broad-screen result `AL`. A BIST equity must clear the full opportunity-funnel gate before a final buy action.

## Output

Start with action, horizon, data timestamp, and confidence. Then show the decisive evidence, valuation or fund quality, technical timing if used, macro transmission, catalysts, bear/base/bull cases, invalidation, quantity/cost, and missing evidence.
