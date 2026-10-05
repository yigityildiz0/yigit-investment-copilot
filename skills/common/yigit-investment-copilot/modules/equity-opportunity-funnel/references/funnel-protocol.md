# Funnel protocol

## 0. Mandate and universe

Define market, benchmark, currency, horizon, style, liquidity floor, market-cap constraints, prohibited instruments, budget and risk posture. Use all reliably covered eligible common shares or the complete requested sector/theme. For broad BIST or US searches, cover at least 90% of the stated membership and at least `min(100, total membership)` names before claiming a broad-market winner. Otherwise disclose the smaller coverage, label the result best within the covered set, and keep it below recommendation grade until the validator passes.

Reconcile `total = covered + not-covered` and `covered = eligible + excluded`. Store the exact source membership rows, covered-ticker ledger and SHA-256 identifiers for the membership and screen artifacts. Verify the membership source with `finance-evidence-guard` module; do not trust a self-declared universe count. Every eligible covered ticker must appear once in the structured screened stage. Every covered exclusion needs a ticker and reason. Exclude only with a stated rule: stale/missing filings, suspended trading, inaccessible share class, insufficient liquidity, incompatible price/lot, extreme spread, corporate action ambiguity, or mandate conflict. Do not exclude a name merely because it is unfamiliar.

## 1. Broad screen

Run several lanes rather than one blended score:

- Quality/financial resilience
- Growth and estimate revision
- Valuation and expectations gap
- Dated catalyst/event
- Momentum and technical regime
- High-upside asymmetry
- Contrarian/reversal with balance-sheet protection

Record raw metrics, source date, missing fields and lane ranks. A composite score may prioritize research but cannot create conviction.

## 2. Medium diligence

Target 8–12 names or the top 10–20% of a small universe. For each, inspect:

- Exact identity, last price and liquidity
- Latest filing and material subsequent disclosures
- Revenue/profit/cash-flow direction and balance sheet
- Sector-specific KPI and peer position
- Valuation and what must be priced in
- Dated catalysts within the horizon
- Technical regime and event/gap risk
- Governance, dilution and one obvious disqualifier

Advance only names with a plausible edge and no unresolved critical blocker.

## 3. Full diligence

Target 3–5 names. Build a falsifiable thesis, business/sector view, normalized financials, valuation range, catalysts, technical timing, probability distribution, downside mechanism, liquidity/execution plan and portfolio effect. Use primary filings and current market evidence.

## 4. Red team and recycle

Require independent contradiction search and arithmetic/source recheck. When a finalist fails, add it to the graveyard with `failure_stage`, `reason`, `evidence`, and `re-entry_condition`; promote the next name and repeat the same stage. Do not replace it with an unanalyzed ticker.

If all finalists fail:

1. Diagnose whether the screen over-weighted one factor or the universe was too narrow.
2. Run one materially different second pass.
3. If no candidate clears, state `NO EDGE` and show the best conditional watchlist rather than fabricating a winner.

## Status vocabulary

- `SCREENED`: passed mechanical eligibility only.
- `ADAY`: deserves medium diligence; not a trade recommendation.
- `FİNALİST`: undergoing full diligence; not yet approved.
- `ÖNERİ SINIFI`: cleared the final gate.
- `ELENDİ`: failed with a recorded reason and possible re-entry condition.
