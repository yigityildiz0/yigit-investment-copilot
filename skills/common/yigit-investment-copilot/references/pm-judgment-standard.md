# Portfolio-manager judgment standard

The layer that turns research into a decision a seasoned portfolio manager would sign. Apply it to every named-stock decision, every finalist and every sell review. Actions and their meanings live in [decision-contract.md](decision-contract.md); this file defines how to reach them.

## 1. Seven questions before any action

Answer each in one or two sentences. An unanswered question caps confidence at "low" and usually means `İZLE` or `KANIT BEKLE`.

1. **What is mispriced, versus what?** Name the variable the market has wrong (volume, margin, rate path, asset value, duration of growth) and the number the market implies for it. "Cheap on P/E" is not an answer.
2. **What is already priced in?** Reverse the price: implied growth (`valuation_models.py reverse-dcf`), implied sustainable ROE (`pb-roe`), consensus targets and surprise history (`expectations` lane). Good news that everyone expects is not an edge.
3. **What evidence would prove the thesis?** A dated, observable event: a quarterly margin, a KAP order announcement, a tariff decision, a capacity start-up.
4. **What would kill it?** A non-price condition written before entry (thesis tracker `kill`), plus the price level where the market is telling you that you are wrong.
5. **Why now?** Catalyst path inside the horizon, regime permission, positioning or valuation extreme. Without a "why now" the right action is usually `İZLE`.
6. **What would change the action?** The specific new fact that moves `İZLE → YENİ AL`, `TUT → AZALT` or `YENİ AL → PAS`. Write it; it becomes the alert.
7. **What evidence is missing?** List it with how and when it can be obtained. Missing decisive evidence → `KANIT BEKLE` with the date.

## 2. Label every claim

Each material statement in an analysis carries one label. Mixed labels are the most common source of false confidence.

| Label | Meaning | Example |
|---|---|---|
| `GERÇEK` | Verified fact with source and date | "2026/06 net profit 3.0 bn TL (KAP financial report, 17.08.2026)" |
| `YÖNETİM` | Management claim, guidance or target | "Company expects 20% volume growth" |
| `KONSENSÜS` | Analyst consensus, targets, ratings | "Median target 58 TL, 7 analysts" |
| `PİYASA` | Market-implied data | "Price implies 24% annual FCF growth for 10 years" |
| `MODEL` | Output of our scripts or models | "P10–P90 range 41–53 (log-normal, zero drift)" |
| `VARSAYIM` | Our input assumption | "Cost of equity 34% nominal TRY" |
| `YARGI` | Portfolio-manager judgment | "Market underestimates the export ramp" |

Rules: a `YARGI` never appears without the `GERÇEK`/`PİYASA` facts it rests on; a `MODEL` number never appears without its main `VARSAYIM`; `YÖNETİM` and `KONSENSÜS` are opinions with incentives.

## 3. Valuation standard

1. **Anchor to the current price.** Every valuation answers "what is it worth relative to today's price and why the gap closes", not "what is it worth in the abstract".
2. **Bridge from consensus.** Show where our numbers differ from consensus or management (revenue, margin, multiple) and why. No difference → no edge on valuation.
3. **Rerating mechanism.** Name what changes the multiple: earnings surprise, deleveraging, index inclusion, dividend policy, governance change, rate cuts. A multiple does not rise because we think it should.
4. **Mechanical downside.** Value if the thesis fails: trough earnings × trough multiple, net asset value with a governance discount, book value for banks at through-cycle ROE. This number sizes the position more than the upside does.
5. **Scenario skew versus the hurdle.** Probability-weighted return compared with the hurdle for the same horizon: the TRY money-market / deposit rate (policy rate as proxy) plus an equity risk premium. A stock that only matches the deposit rate with equity risk is a `PAS`.
6. **Underwriteable versus optical upside.** Underwriteable: follows from verifiable operating facts at a sober multiple. Optical: needs multiple expansion, a narrative or a perfect macro path. Size only on the underwriteable part.
7. **Currency and inflation discipline.** TRY flows with TRY rates, real with real, USD with USD plus country risk (`valuation_models.py coe`); TMS 29 equity with real rates, banks (no TMS 29) with nominal.

## 4. Risk lens

- **Binding constraint.** Name what limits size today: liquidity (order ≤1–2% of daily value), the loss budget at the stop, the gap scenario (limit-down open), concentration or sector cap, or the event calendar. The smallest of these sets the size.
- **Retained exposure.** After stops and diversification, what risk is still carried (FX, rates, a single customer, a controlling shareholder, a regulatory decision)? State it.
- **Hedge or stop failure.** How the protection fails: limit-down gap through the stop, trading halt, VBTS single-price session, correlation spike. Size for that loss, not only for the stop distance.
- **Size-down alternative.** Before rejecting an idea, check whether a starter position, a staged entry or a basket of two peers expresses it with acceptable risk. Before accepting one, check that a smaller size would not deliver most of the benefit.

## 5. Screen-grade versus recommendation-grade

When data is thin (no filing read, stale price, sandbox without internet, no committee pass), the output is **screen-grade**: label it `ADAY`, give the conditional structure (entry gate, the fields still needed, the quantity formula) and stop there. Recommendation-grade requires the funnel's final gate. Never dress a screen-grade result in recommendation language.

## 6. Deliverable quality bar

- One-page answer first, detail on request; the first line is the action and the horizon.
- Every number ties out: totals add up, percentages match their bases, units and currencies are stated, dates are consistent (see the tie-out checklist in [report-templates.md](report-templates.md)).
- Sources carry dates; delayed data says so.
- Record the decision in the forecast ledger (`forecast_ledger.py add --thesis --kill --benchmark-price`) so the outcome and lesson can be scored later, and read `forecast_ledger.py history --ticker KOD` before re-analysing a name.
