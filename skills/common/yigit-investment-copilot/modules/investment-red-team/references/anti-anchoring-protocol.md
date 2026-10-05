# Anti-anchoring reconsideration protocol

Use this protocol when the user asks whether the assistant is sure, requests a repeat analysis, challenges a recommendation, or asks if something more sensible exists.

## Reset the decision

1. Write the objective without naming the incumbent instrument: desired horizon, currency, available budget, acceptable loss, liquidity need, permitted products and portfolio role.
2. Freeze a common evidence cutoff. Do not compare an old price for one option with a current price for another.
3. If practical, do an independent screen from the objective before inspecting the prior rationale. The prior recommendation enters the candidate set but receives no incumbent bonus.
4. Record what evidence would make the incumbent lose. Do not move that threshold after seeing the alternatives.

## Build the challenger set

Include:

- the prior recommendation;
- the best same-asset-class challenger found through the applicable broad screen;
- each cross-asset challenger that can realistically serve the same objective, such as a fund/ETF, gold, fixed income/cash, crypto or a derivative;
- `do nothing` or cash as a real option.

Cross-asset comparison is conditional, not decorative. Exclude an option when its horizon, risk, access, denomination, liquidity, tax, minimum size or payoff shape makes it non-comparable. Give the exclusion reason. Do not add a weak alternative merely to be different.

## Compare symmetrically

Use one table and one evidence cutoff for every viable option:

- bear/base/bull outcome and probability-weighted return;
- maximum plausible and tail loss;
- thesis and catalyst path within the stated horizon;
- evidence quality and model uncertainty;
- liquidity, spread, fees, tax, settlement and switching cost;
- correlation and contribution to the existing portfolio;
- operational feasibility on the user's platform and budget.

Apply the same depth to the winning challenger as to the incumbent. A coarse challenger cannot defeat a fully researched incumbent, and a familiar incumbent cannot defeat a deeply researched challenger by name recognition.

For structured validation, preserve a `fresh_pass` record with the objective stated without the incumbent, the result reached before inspecting the old rationale, the precommitted threshold that makes the incumbent lose, and confirmation that the old rationale was reviewed only afterward. Give every option the common data cutoff, bear/base/bull cases, tail loss, catalyst, costs/tax/spread, evidence ledger and `equal_depth: true`.

## Bias checks

Explicitly test:

- anchoring to the first ticker or target price;
- confirmation bias in source selection;
- sunk-cost or endowment bias caused by an existing position;
- consistency pressure caused by the assistant's earlier answer;
- recency and familiarity bias;
- novelty bias that rewards a different answer merely because it is different.

## Resolve

Keep two separate labels: `evidence_delta` is `UNCHANGED`, `UPDATED`, `INVALIDATED`, or `CORRECTION`; `decision_outcome` is `CONFIRMED`, `REPLACED`, `WAIT`, `INVALIDATED`, or `CORRECTION`. Show the decisive comparison and the smallest new fact or threshold that would change the outcome again. A confirmed recommendation must explain why the strongest challenger lost. A replacement must receive full recommendation-grade diligence before action.
