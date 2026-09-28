# Module: investment-committee

> Part of the `yigit-investment-copilot` skill. Paths below are relative to this module folder (`modules/investment-committee/`).
> Original trigger scope: Run a structured investment committee on a finalist or a named stock before any buy, add, hold or sell decision: four analyst briefs (fundamental, technical/flow, news/KAP, macro/sector), a bull-versus-bear debate, a panel of classic investor lenses, a risk committee (aggressive, neutral, conservative) and a portfolio-manager decision with probability-weighted scenarios. Use after the funnel's deep dive, for "alınır mı / satılır mı" on a named stock, for "farklı açılardan değerlendir", "Buffett olsa alır mı", "boğa ve ayı senaryosu", or when evidence conflicts. Feeds the red team; does not replace it.

# Investment Committee

The committee turns evidence into a decision without letting one story dominate. Inspired by multi-agent research frameworks (analysts → bull/bear researchers → trader → risk team → portfolio manager) and by the checklists of well-documented investors. Read [references/debate-protocol.md](references/debate-protocol.md) and [references/investor-lenses.md](references/investor-lenses.md).

## Inputs (must exist before the meeting)

Evidence pack for the stock: identity and live price/time; KAP filings and events (`news-catalyst-intelligence`); normalised financials and valuation (`public-equity-research`); technical state and levels (`technical-quant-analysis`); regime and sector context (`market-regime-analysis`); flow notes if available (`bist-microstructure-flow`); horizon, budget and loss limit from intake. Missing inputs are listed, not invented.

## Meeting order

1. **Analyst briefs (4 × ≤120 words).** Fundamental, technical/flow, news/KAP/sentiment, macro/sector. Each ends with direction (+/0/−), strength (1–3), evidence quality (A/B/C) and the one fact that would flip it.
2. **Bear case first, then bull case.** Writing the bear case first counters anchoring on the original idea. Each side cites evidence from the pack, quantifies its scenario (price range, probability, timing) and names its kill condition.
3. **Rebuttal round (≥1, ≤3).** Each side answers the other's two strongest points with evidence. Stop when no new evidence appears.
4. **Investor-lens panel.** Score the relevant lenses (not all) for the horizon: long-term → Graham, Buffett/Munger, Fisher, Lynch, Greenblatt, Damodaran, Marks, Pabrai, Jhunjhunwala; contrarian/special situations → Burry, Ackman; innovation/high-multiple → Wood (with a hype test); swing/trend → O'Neil, Minervini, Weinstein, Livermore/Darvas, Druckenmiller; always → Taleb (fragility) and accounting forensics. Each lens: pass / mixed / fail + one-line reason.
5. **Risk committee.** Aggressive, neutral and conservative members each propose action, size (as % of the loss budget), entry method and stop logic. Conservative must address gap/limit-down risk, liquidity and regime.
6. **Portfolio-manager decision.** First answer the seven PM questions and label the decisive claims (`../../references/pm-judgment-standard.md`). Then choose one: `YENİ AL`, `SPEKÜLATİF AL`, `ARTIR`, `TUT`, `AZALT`, `SAT`, `İZLE`, `KANIT BEKLE`, `YENİDEN DEĞERLENDİR`, `KORUMA`, `PAS`, `AKSİYON YOK`. Give bear/base/bull ranges with probabilities that sum to 100% when the evidence supports numbers, the expected value vs cash/deposit alternative, the binding constraint on size, confidence (high/medium/low) and the decisive reason. Read `forecast_ledger.py history --ticker KOD --lessons-only` first when the name was analysed before.
7. **Hand-off.** Send the decision to `investment-red-team` (independent challenge), then `pre-trade-investment-gate`, then `trade-management-exits` for the written plan, then log the forecast in the ledger.

## Rules

- Evidence beats eloquence: every claim cites the pack; unsupported claims are struck.
- Disagreement is information. Do not average bull and bear into a lukewarm middle; decide which evidence is stronger and why.
- A great company at a bad price, in a falling market regime, can still be `İZLE`.
- "No trade" and cash/deposit are always on the table; in Türkiye the risk-free alternative is high, so a stock must beat it after risk.
- Keep the whole meeting internal unless the user asks; show the decision, the strongest bull and bear points, lens summary and risk-committee sizing.

## Output

Decision line · bear/base/bull table with probabilities, targets and triggers · strongest bull point · strongest bear point · lens scorecard (compact) · risk-committee sizing range and chosen size · kill conditions · what would change the decision · hand-off status (red team / gate / plan / ledger).
