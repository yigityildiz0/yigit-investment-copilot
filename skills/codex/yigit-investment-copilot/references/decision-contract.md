# Decision contract

## Minimum evidence

- Exact instrument identity and currency
- Current timestamped price or NAV with delay status
- Relevant primary filing, fund document, or official product terms
- Horizon and decision being made
- Downside and invalidation condition
- Calculation inputs and units

For an open-ended stock recommendation, minimum evidence also includes the screened universe and coverage count, staged shortlist, full diligence on finalists, runner-up comparison, and the final recommendation gate. A screen result is an `ADAY`, never an `AL`.

## Action meanings

- `YENİ AL`: favorable risk/reward for a new position under stated assumptions.
- `SPEKÜLATİF AL`: high full-loss probability but favorable enough asymmetry or catalyst for an explicitly disposable, capped budget.
- `ARTIR`: add only within stated concentration and loss limits.
- `TUT`: thesis intact; expected benefit of changing is not material.
- `AZALT`: concentration, valuation, catalyst, liquidity, or thesis risk is excessive.
- `SAT`: thesis is broken or downside dominates after costs and alternatives.
- `İZLE`: promising but price, timing, or evidence is not ready.
- `KANIT BEKLE`: the thesis is attractive but one named, dated piece of evidence decides it (a filing, an order, a regulatory decision); state the evidence and the date, act only after it arrives.
- `YENİDEN DEĞERLENDİR`: the thesis or the facts under it changed materially (earnings, management, capital structure, regulation); redo the work before adding or holding at full size.
- `KORUMA`: keep the exposure but reduce one named risk (partial sale before an event, a hedge where the user has access, a tighter stop); state the retained risk.
- `PAS`: not attractive now and not worth monitoring; say what would make it worth a second look.
- `AKSİYON YOK`: identity is unresolved, no defensible edge exists, or an action would require fabricated inputs. Missing executable data alone should instead produce a conditional setup and finalization checklist.

How to reach an action (seven PM questions, claim labels, valuation and risk standards): [pm-judgment-standard.md](pm-judgment-standard.md).

## Scenario requirements

Each bear/base/bull case must contain:

- Price or return range and horizon
- Conditions required
- Catalysts and timing
- What invalidates it
- Liquidity and cost effects
- Confidence and missing evidence

Use probability ranges only when anchored to data or a transparent model. Do not force probabilities to sum to 100 when evidence is too weak; label them qualitative instead.

For high-risk screens, rank candidates using a transparent combination of probability-weighted return, downside, catalyst strength, liquidity/spread, time horizon, and invalidation quality. Do not select solely by maximum theoretical upside.

## Quantity requirements

Report both budget-limited and risk-limited quantities. Round down to the exchange lot or contract size. Include fees, spread where known, stop/invalidation assumptions, total cash used, cash remaining, modeled loss at invalidation, and a warning when gap risk can exceed it.
